#!/usr/bin/env python3
"""Enhance contribution snake to grow progressively as it eats contributions."""

import re
import sys


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
    <!-- Background stars -->
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


def enhance_snake_styles(svg_content):
    """Enhance CSS styles for snake appearance."""
    # Make base cells transparent
    svg_content = re.sub(
        r'\.c\{[^}]+\}',
        '.c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);animation:none 49900ms linear infinite;width:12px;height:12px;opacity:0}',
        svg_content
    )

    # Add snake styles with glow effects
    snake_styles = '''
/* Glow filter for snake head */
<filter id="snakeGlow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2" result="blur"/>
    <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>'''

    return re.sub(r'(</style>)', snake_styles + r'\n\1', svg_content, count=1)


def parse_snake_path(svg_content):
    """Parse each contribution cell's animation: its cell id, the loop % when the
    snake head reaches it, and its real contribution color variable.

    Returns a list of (cell_id, activation_pct, color_var) sorted by activation
    time (the moment the snake head passes that cell during the loop).
    """
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return []

    style = style_match.group(1)

    # Matches: @keyframes c[ID]{[PCT]%{fill:var(--cN) ...}
    # snk names cells with full alphanumeric ids (c0..c9, ca..cz, c10..c1z, ...).
    keyframe_pattern = r'@keyframes (c[0-9a-zA-Z]+)\{([\d.]+)%\{fill:var\((--c\d+)\)'
    matches = re.findall(keyframe_pattern, style)

    # Sort by activation time (head arrival order)
    cells = sorted(matches, key=lambda x: float(x[1]))
    return cells


def create_growing_snake_keyframes(svg_content, initial_length=4, growth_rate=2):
    """
    Rebuild each contribution cell's keyframe so that the graph behaves like the
    Pac-Man contribution animation:

      * Until the snake head arrives, the dot is shown in its REAL contribution
        color (the contribution graph is visible at rest).
      * When the head reaches it, the dot flashes green as the snake head.
      * While the snake body passes, the dot is covered by the neon-green body.
      * Once the snake TAIL passes, the dot is eaten -> fades to opaque 0, i.e.
        it disappears into the space background for the rest of the loop.

    The snake body grows over the loop: it starts at ``initial_length`` segments
    and gains 1 segment every ``growth_rate`` dots eaten, so the tail lags further
    and further behind the head as dots are consumed.

    Args:
        initial_length: Starting snake length (default 4: head + 3 body).
        growth_rate: Number of contributions needed to grow by 1 segment (2).
    """
    cells = parse_snake_path(svg_content)
    if not cells:
        return svg_content

    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return svg_content

    style = style_match.group(1)
    n = len(cells)

    # Snake body length at the moment the head reaches the i-th cell (time order).
    lengths = [initial_length + (i // growth_rate) for i in range(n)]

    # Two-pass look-ahead: a dot eaten at time index i is consumed (tail passes)
    # when the head reaches time index i + lengths[i]. Cells near the end of the
    # loop are never consumed -> they stay as body until 100% and reset to their
    # real color at 0% on the next loop.
    fade_times = [100.0] * n
    for i in range(n):
        tail_idx = i + lengths[i]
        if tail_idx < n:
            fade_times[i] = float(cells[tail_idx][1])

    def create_keyframe_for_cell(cell_id, index, activation_pct, color_var, fade_time):
        """Build the full lifecycle keyframe for one contribution dot."""
        activation = float(activation_pct)
        g = 0.01  # near-instant transition gap (negligible ramp, discrete feel)
        head_w = 0.15  # how long the bright snake head stays lit (% of loop)

        head_end = min(activation + head_w, 99.9)
        fade_start = max(min(fade_time - g, 99.99), activation + g)

        frames = []
        # 1) Real contribution color until the head arrives (also the rest state).
        frames.append(f'0%,{activation:.2f}%{{fill:var({color_var});opacity:1}}')
        # 2) Snake head: bright neon with glow.
        frames.append(f'{activation:.2f}%{{fill:#00FF9D;opacity:1.0;filter:url(#snakeGlow)}}')
        # 3) Snake body covers the eaten dot.
        frames.append(f'{head_end:.2f}%{{fill:#00FF9D;opacity:0.7}}')
        frames.append(f'{fade_start:.2f}%{{fill:#00FF9D;opacity:0.7}}')
        # 4) Tail passes -> dot consumed, gone into the space background.
        frames.append(f'{min(fade_time, 100.0):.2f}%{{fill:#00FF9D;opacity:0}}')
        frames.append('100%{fill:#00FF9D;opacity:0}')

        return f'@keyframes {cell_id}{{{"".join(frames)}}}'

    # Rebuild the style by replacing each cell keyframe block (nested-brace safe).
    keyframe_blocks = re.split(r'(@keyframes c[0-9a-zA-Z]+\{)', style)
    result_parts = [keyframe_blocks[0]]  # Keep everything before the first keyframe

    # index of each cell id in time order, for the construction loop below
    time_index = {cid: idx for idx, (cid, _, _) in enumerate(cells)}

    i = 1
    while i < len(keyframe_blocks):
        if i + 1 < len(keyframe_blocks):
            keyframe_start = keyframe_blocks[i]  # "@keyframes cXX{"
            cell_id_match = re.search(r'c[0-9a-zA-Z]+', keyframe_start)
            if cell_id_match:
                cell_id = cell_id_match.group(0)

                remaining = keyframe_blocks[i + 1]
                # Find the matching closing brace for this keyframe block
                brace_count = 1
                pos = 0
                while pos < len(remaining) and brace_count > 0:
                    if remaining[pos] == '{':
                        brace_count += 1
                    elif remaining[pos] == '}':
                        brace_count -= 1
                    pos += 1

                after_keyframe = remaining[pos:]

                if cell_id in time_index:
                    idx = time_index[cell_id]
                    new_keyframe = create_keyframe_for_cell(
                        cell_id, idx,
                        cells[idx][1], cells[idx][2],
                        fade_times[idx],
                    )
                    result_parts.append(new_keyframe)
                else:
                    result_parts.append(keyframe_start + remaining[:pos])

                result_parts.append(after_keyframe)
                i += 2
            else:
                result_parts.append(keyframe_start)
                i += 1
        else:
            result_parts.append(keyframe_blocks[i])
            i += 1

    enhanced_style = ''.join(result_parts)

    # Replace the style section
    svg_content = re.sub(
        r'<style>.*?</style>',
        f'<style>{enhanced_style}</style>',
        svg_content,
        flags=re.DOTALL,
        count=1
    )

    return svg_content


def main(input_path, output_path=None, growth_rate=2):
    """Main enhancement function."""
    if output_path is None:
        output_path = input_path

    # Read input SVG
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {input_path} ({len(svg_content)} chars)...")

    # Apply enhancements
    svg_content = add_space_background(svg_content)
    svg_content = enhance_snake_styles(svg_content)
    svg_content = create_growing_snake_keyframes(svg_content, initial_length=4, growth_rate=growth_rate)

    # Write output SVG
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Enhanced SVG saved to {output_path} ({len(svg_content)} chars)")
        print("Enhancements applied:")
        print("  ✓ Space nebula and starfield background")
        print(f"  ✓ Snake grows by 1 segment every {growth_rate} contributions")
        print("  ✓ Contribution dots visible in their real colors until eaten")
        print("  ✓ Snake head glows brightly when active")
        print("  ✓ Eaten dots disappear into the space background after the tail passes")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 snake_growth_enhancer.py <input_svg> [output_svg] [growth_rate]")
        print("  input_svg:   Path to Platane/snk output SVG")
        print("  output_svg:  Path for enhanced SVG (optional)")
        print("  growth_rate: Contributions per growth segment (default: 2)")
        sys.exit(1)

    growth_rate = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, growth_rate)
