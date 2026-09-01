#!/usr/bin/env python3
"""Rigid-body contribution snake (Pac-Man style, no trails).

Transforms a Platane/snk SVG so that:

  * every contribution dot shows its real contribution color and vanishes the
    instant the snake head touches it;
  * a rigid purple snake body follows the head's exact route around the board;
    it starts at 4 blocks (head + 3 body) and grows by one block every
    3 dots eaten;
    eaten;
  * the whole loop runs slower by a speed factor (default 1.5x).

How the rigid body works
------------------------
snk moves the head sprite (.s) through waypoints with CSS translate keyframes.
We build ONE closed <path> through those waypoints (offset to the cell
centers) and render it as a purple stroke. A CSS stroke-dasharray /
stroke-dashoffset animation limits the visible part of the stroke to exactly
the last `length` cells of the route behind the moving head:

    visible window = [head_arc - body_length, head_arc]
    stroke-dashoffset = body_length - head_arc
    stroke-dasharray  = body_length, route_total - body_length

Because dashoffset keyframes are emitted at every head waypoint (plus every
growth instant), the window tracks the head exactly - pauses, corner turns
and the glide back to the start included - and each eaten dot slides the tail
one block backward.

Usage: python3 snake_growth_enhancer.py <input_svg> [output_svg] [speed_factor]
"""

import re
import sys

CELL = 16.0          # distance between adjacent cell centers in the snk grid
INITIAL_BLOCKS = 4   # snake length at loop start (head + body blocks)
GROWTH_EVERY = 3     # grow +1 body block per this many dots eaten
NEON_COLOR = "#C84BFF"  # bright neon violet for the glowing snake body
SPRITE_CENTER = 8.0  # head sprite center offset from its translate origin
EPS = 0.01           # near-instant transition ramp, in % of the loop


def add_space_background(svg_content):
    """Add a space-themed background to the SVG."""
    background = '''<!-- Space Background -->
<rect width="100%" height="100%" fill="#000000"/>
<!-- Nebula -->
<g id="nebula" fill-opacity="0.05">
    <circle cx="200" cy="80" r="80" fill="#4B0082"/>
    <circle cx="600" cy="120" r="70" fill="#8A2BE2"/>
    <circle cx="400" cy="30" r="60" fill="#9400D3"/>
    <circle cx="750" cy="50" r="50" fill="#8B008B"/>
</g>
<!-- Stars -->
<g id="stars" fill-opacity="0.6">
    <circle cx="100" cy="50" r="0.5" fill="#FFFFFF"/>
    <circle cx="200" cy="100" r="0.3" fill="#FFFFFF"/>
    <circle cx="300" cy="30" r="0.4" fill="#FFFFFF"/>
    <circle cx="400" cy="150" r="0.2" fill="#FFFFFF"/>
    <circle cx="500" cy="80" r="0.3" fill="#FFFFFF"/>
    <circle cx="600" cy="40" r="0.5" fill="#FFFFFF"/>
    <circle cx="700" cy="120" r="0.2" fill="#FFFFFF"/>
    <circle cx="800" cy="60" r="0.4" fill="#FFFFFF"/>
    <!-- Twinkling stars -->
    <circle cx="150" cy="80" r="0.8" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.2;1;0.2" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle cx="450" cy="100" r="0.6" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.3;0.9;0.3" dur="4s" repeatCount="indefinite"/>
    </circle>
</g>'''
    return re.sub(r'(<svg[^>]*>)', r'\1\n    ' + background, svg_content, count=1)


def strip_counter(svg_content):
    """Remove a previously injected dots-eaten counter (defensive no-op)."""
    svg_content = re.sub(r'\.snkcnt\{.*?(?=</style>)', '', svg_content,
                         flags=re.DOTALL)
    svg_content = re.sub(r'<defs><filter id="snkcntglow".*?</g>\s*(?=</svg>)',
                         '', svg_content, flags=re.DOTALL)
    return svg_content


def parse_head_waypoints(style):
    """[(pct, x, y)] of the head sprite's translate keyframes, time-sorted."""
    m = re.search(r'@keyframes s0\{(.*?)\}\.s\.s0', style, re.DOTALL)
    if not m:
        raise SystemExit('head sprite keyframes (s0) not found')
    entries = []
    seg = re.compile(
        r'((?:\d+(?:\.\d+)?%,)*(?:\d+(?:\.\d+)?))%'
        r'\{transform:translate\((-?[\d.]+)px,(-?[\d.]+)px\)\}')
    for sm in seg.finditer(m.group(1)):
        x, y = float(sm.group(2)), float(sm.group(3))
        for p in sm.group(1).split(','):
            entries.append((float(p.rstrip('%')), x, y))
    entries.sort(key=lambda e: e[0])
    wps = []
    for e in entries:
        if wps and abs(e[0] - wps[-1][0]) < 1e-6:
            wps[-1] = e
        else:
            wps.append(e)
    return wps


def parse_cells(style):
    """Sorted [(activation_pct, cell_id, color_var)] for every dot."""
    name_re = re.compile(r'@keyframes (c[0-9a-zA-Z]+)\{')
    seg_re = re.compile(
        r'((?:\d+(?:\.\d+)?%,)*(?:\d+(?:\.\d+)?))%\{fill:var\((--c\d+)\)')
    cells = []
    i = 0
    while True:
        m = name_re.search(style, i)
        if not m:
            break
        open_b = m.end() - 1  # the regex consumed the keyframes' opening brace
        j = open_b + 1
        depth = 1
        while j < len(style) and depth > 0:
            if style[j] == '{':
                depth += 1
            elif style[j] == '}':
                depth -= 1
            j += 1
        sm = seg_re.search(style[open_b + 1:j - 1])
        if sm:
            pct = max(float(p.rstrip('%')) for p in sm.group(1).split(','))
            cells.append((pct, m.group(1), sm.group(2)))
        i = j
    cells.sort()
    return cells


def cell_keyframe(pct, cid, color_var):
    """Real color at rest, gone the instant the head touches the dot."""
    gone = min(pct + EPS, 99.99)
    return (
        f'@keyframes {cid}{{0%,{pct:.2f}%{{fill:var({color_var});opacity:1}}'
        f'{gone:.2f}%{{fill:var(--ce);opacity:0}}'
        f'100%{{fill:var(--ce);opacity:0}}}}'
    )


def rebuild_cell_keyframes(style, cells):
    mapping = {cid: cell_keyframe(pct, cid, var) for pct, cid, var in cells}
    name_re = re.compile(r'@keyframes (c[0-9a-zA-Z]+)\{')
    out = []
    i = 0
    while True:
        m = name_re.search(style, i)
        if not m:
            out.append(style[i:])
            break
        out.append(style[i:m.start()])
        open_b = m.end() - 1  # the regex consumed the keyframes' opening brace
        j = open_b + 1
        depth = 1
        while j < len(style) and depth > 0:
            if style[j] == '{':
                depth += 1
            elif style[j] == '}':
                depth -= 1
            j += 1
        out.append(mapping.get(m.group(1), style[m.start():j]))
        i = j
    return ''.join(out)


def build_body(style, cells):
    """Return (sb0_keyframes, path_d, route_total_px)."""
    wps = parse_head_waypoints(style)
    pts = [(x + SPRITE_CENTER, y + SPRITE_CENTER) for _, x, y in wps]
    arcs = [0.0]
    for a, b in zip(pts, pts[1:]):
        arcs.append(arcs[-1] + ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5)
    # close the route if the last waypoint is not the first one
    gap = ((pts[0][0] - pts[-1][0]) ** 2 +
           (pts[0][1] - pts[-1][1]) ** 2) ** 0.5
    if gap >= 0.5:
        pts.append(pts[0])
        arcs.append(arcs[-1] + gap)
        wps.append((100.0, wps[0][1], wps[0][2]))
    total = arcs[-1]
    times = [w[0] for w in wps]
    activations = [pct for pct, _, _ in cells]

    def arc_at(t):
        if t <= times[0]:
            return arcs[0]
        for k in range(1, len(times)):
            if t <= times[k]:
                f = (t - times[k - 1]) / (times[k] - times[k - 1])
                return arcs[k - 1] + f * (arcs[k] - arcs[k - 1])
        return arcs[-1]

    def length_at(t):
        n = sum(1 for a in activations if a <= t + 1e-9)
        return (INITIAL_BLOCKS - 1 + n // GROWTH_EVERY) * CELL

    growth_ts = []
    for a in activations:
        growth_ts += [a - EPS, a, a + EPS]

    offset_props = {}
    for t in sorted(set([0.0, 100.0] + times + growth_ts)):
        if t < 0.0 or t > 100.0:
            continue
        key = f'{t:.3f}'
        offset_props.setdefault(key, []).append(
            f'stroke-dashoffset:{length_at(t) - arc_at(t):.2f}')

    arr_props = {}
    for t in sorted(set([0.0, 100.0] + growth_ts)):
        if t < 0.0 or t > 100.0:
            continue
        length = length_at(t)
        arr_props[f'{t:.3f}'] = \
            f'stroke-dasharray:{length:.0f},{total - length:.0f}'

    frames = []
    for key in sorted(set(offset_props) | set(arr_props), key=float):
        props = list(offset_props.get(key, []))
        if key in arr_props:
            props.append(arr_props[key])
        frames.append(f'{key}%{{{";".join(props)}}}')
    body_kf = '@keyframes sb0{' + ''.join(frames) + '}'
    path_d = 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in pts) + ' Z'
    return body_kf, path_d, total


def scale_durations(svg_content, factor):
    def repl(m):
        return f'{int(round(int(m.group(1)) * factor))}ms'
    return re.sub(r'(\d+)ms', repl, svg_content)


def main(input_path, output_path=None, speed=1.5):
    if output_path is None:
        output_path = input_path
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    if 'snakeBody' in svg_content or '@keyframes sb0' in svg_content:
        print('Input already contains the rigid-body enhancement - '
              'regenerate from a fresh snk SVG instead.', file=sys.stderr)
        sys.exit(1)

    print(f'Processing {input_path} ({len(svg_content)} chars)...')
    svg_content = strip_counter(svg_content)
    svg_content = add_space_background(svg_content)

    style_m = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_m:
        raise SystemExit('no <style> section found - not a snk SVG?')
    style = style_m.group(1)

    sm = re.search(r'\.s\{[^}]*?(\d+)ms', style)
    loop_dur = int(sm.group(1)) if sm else 49900

    cells = parse_cells(style)
    if not cells:
        raise SystemExit('no contribution cells found - not a snk SVG?')
    body_kf, path_d, total = build_body(style, cells)

    # hide the empty grid cells, keep the per-cell animations running
    style = rebuild_cell_keyframes(style, cells)
    style = re.sub(
        r'\.c\{[^}]*\}',
        f'.c{{shape-rendering:geometricPrecision;fill:var(--ce);'
        f'stroke-width:1px;stroke:var(--cb);'
        f'animation:none {loop_dur}ms linear infinite;'
        f'width:12px;height:12px;opacity:0}}',
        style, count=1)
    snake_css = (
        f'.snakeBody{{fill:none;stroke:{NEON_COLOR};stroke-width:12px;'
        f'stroke-linecap:round;stroke-linejoin:round;'
        f'animation:none {loop_dur}ms linear infinite;'
        f'animation-name:sb0;filter:url(#snakeGlow)}}')
    style = style + '\n' + snake_css + '\n' + body_kf + '\n'
    svg_content = (svg_content[:style_m.start()] +
                   f'<style>{style}</style>' +
                   svg_content[style_m.end():])

    # glow filter definition (vivid neon halo used by the snake body)
    filt = (
        '<defs><filter id="snakeGlow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="7" result="blur"/>'
        f'<feFlood flood-color="{NEON_COLOR}" flood-opacity="0.9" result="color"/>'
        '<feComposite in="color" in2="blur" operator="in" result="glow"/>'
        '<feMerge><feMergeNode in="glow"/><feMergeNode in="glow"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
    )
    svg_content = svg_content.replace('</svg>', filt + '</svg>', 1)

    # the rigid body path, drawn under the head sprite
    svg_content = re.sub(
        r'(<rect class="s )',
        lambda m: f'<path class="snakeBody" d="{path_d}"/>' + m.group(1),
        svg_content, count=1)

    svg_content = scale_durations(svg_content, speed)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    eaten = len(cells)
    print(f'Enhanced SVG saved to {output_path} ({len(svg_content)} chars)')
    print('Enhancements applied:')
    print('  - Space nebula and starfield background')
    print(f'  - Glowing snake body: starts at {INITIAL_BLOCKS} blocks, '
          f'+1 block per {GROWTH_EVERY} dots eaten '
          f'(final {INITIAL_BLOCKS + eaten // GROWTH_EVERY} blocks)')
    print(f'  - Body route follows the head exactly '
          f'({total:.0f}px closed path)')
    print('  - Dots vanish the instant the head touches them')
    print(f'  - Loop slowed by x{speed} ({loop_dur}ms -> '
          f'{int(round(loop_dur * speed))}ms)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 snake_growth_enhancer.py <input_svg> '
              '[output_svg] [speed_factor]')
        print('  input_svg:   Path to Platane/snk output SVG')
        print('  output_svg:  Path for enhanced SVG (optional)')
        print('  speed_factor: Loop duration multiplier (default 1.5 = slower)')
        sys.exit(1)
    _speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, _speed)
