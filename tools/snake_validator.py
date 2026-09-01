#!/usr/bin/env python3
"""Validate the rigid-body contribution snake SVG.

Checks:
  1. every contribution dot shows its real color at rest, vanishes right
     after the head touches it, and never re-appears within the loop;
  2. a rigid .snakeBody path with an sb0 dash animation exists;
  3. the body starts at 4 blocks and grows exactly +1 block (16px) per dot;
  4. the body's visible window equals [head_arc - length, head_arc] at every
     sampled loop time (rigid follow, in sync with the head sprite);
  5. all loop durations (.c/.s/.snakeBody/.snkcnt) are identical and slower
     than the stock 49900ms.

Exit code is non-zero on any failing check so it can be used in CI.

Usage: python3 snake_validator.py [path-to-enhanced-svg]
"""

import re
import sys

CELL = 16.0
INITIAL_BLOCKS = 4
EPS = 0.01
TOL = 1.0  # px tolerance for the rigid-follow check


def get_style(svg_content):
    m = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not m:
        raise SystemExit('no <style> section found')
    return m.group(1)


def parse_waypoints(style):
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
    """{cell_id: (activation_pct_or_None, [(pct, props), ...])}"""
    name_re = re.compile(r'@keyframes (c[0-9a-zA-Z]+)\{')
    cells = {}
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
        inner = style[open_b + 1:j - 1]
        segs = [(float(p), pr) for p, pr in
                re.findall(r'([\d.]+)%\{([^}]*)\}', inner)]
        act = None
        am = re.search(r'((?:[\d.]+%,)*[\d.]+)%\{fill:var\(--c\d+\)', inner)
        if am:
            act = max(float(p.rstrip('%')) for p in am.group(1).split(','))
        cells[m.group(1)] = (act, segs)
        i = j
    return cells


def parse_sb0(style):
    m = re.search(r'@keyframes sb0\{', style)
    if not m:
        return None
    open_b = style.find('{', m.start())
    j = open_b + 1
    depth = 1
    while j < len(style) and depth > 0:
        if style[j] == '{':
            depth += 1
        elif style[j] == '}':
            depth -= 1
        j += 1
    inner = style[open_b + 1:j - 1]
    off, arr = [], []
    for p, props in re.findall(r'([\d.]+)%\{([^}]*)\}', inner):
        t = float(p)
        dm = re.search(r'stroke-dashoffset:(-?[\d.]+)', props)
        am = re.search(r'stroke-dasharray:([\d.]+),([\d.]+)', props)
        if dm:
            off.append((t, float(dm.group(1))))
        if am:
            arr.append((t, float(am.group(1)), float(am.group(2))))
    off.sort()
    arr.sort()
    if not off or not arr:
        return None
    return off, arr


def interp(track, t, idx):
    if t <= track[0][0]:
        return track[0][idx]
    if t >= track[-1][0]:
        return track[-1][idx]
    for k in range(1, len(track)):
        if t <= track[k][0]:
            t0, v0 = track[k - 1][0], track[k - 1][idx]
            t1, v1 = track[k][0], track[k][idx]
            if t1 == t0:
                return v1
            f = (t - t0) / (t1 - t0)
            return v0 + f * (v1 - v0)
    return track[-1][idx]


def run(path):
    svg = open(path, encoding='utf-8').read()
    style = get_style(svg)
    failures = []

    def check(label, ok, detail=''):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" +
              (f"  ({detail})" if detail else ''))
        if not ok:
            failures.append(label)

    wps = parse_waypoints(style)
    pts = [(x + 8.0, y + 8.0) for _, x, y in wps]
    arcs = [0.0]
    for a, b in zip(pts, pts[1:]):
        arcs.append(arcs[-1] + ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5)
    times = [w[0] for w in wps]

    def arc_at(t):
        if t <= times[0]:
            return arcs[0]
        for k in range(1, len(times)):
            if t <= times[k]:
                f = (t - times[k - 1]) / (times[k] - times[k - 1])
                return arcs[k - 1] + f * (arcs[k] - arcs[k - 1])
        return arcs[-1]

    cells = parse_cells(style)
    acts = sorted(v[0] for v in cells.values() if v[0] is not None)

    def length_at(t):
        n = sum(1 for a in acts if a <= t + 1e-9)
        return (INITIAL_BLOCKS - 1 + n) * CELL

    print(f'cells parsed: {len(cells)}   head waypoints: {len(wps)}   '
          f'route: {arcs[-1]:.0f}px')

    # 1) dot lifecycle
    bad_rest, bad_gone, reappeared = [], [], []
    for cid, (act, segs) in cells.items():
        props_all = ';'.join(pr for _, pr in segs)
        if act is None or 'opacity:0' not in props_all \
                or 'fill:var(--c' not in props_all:
            bad_rest.append(cid)
            continue

        def state_at(t, segs=segs):
            cur = segs[0][1]
            for p, pr in segs:
                if p <= t:
                    cur = pr
            return cur

        rest = state_at(0.001)
        if 'opacity:1' not in rest or 'fill:var(--c' not in rest:
            bad_rest.append(cid)
        gone_t = None
        for p, pr in segs:
            if 'opacity:0' in pr and p > 0:
                gone_t = p if gone_t is None else min(gone_t, p)
        if gone_t is None or gone_t > act + 0.05:
            bad_gone.append(cid)
        seen_gone = False
        for p, pr in segs:
            if 'opacity:0' in pr and p > 0:
                seen_gone = True
            elif seen_gone and 'opacity:1' in pr and p > 0:
                reappeared.append((cid, p))
    check('all dots show their real color at rest', not bad_rest,
          str(bad_rest[:4]))
    check('all dots vanish right after the head touches them', not bad_gone,
          str(bad_gone[:4]))
    check('eaten dots never re-appear within the loop', not reappeared,
          str(reappeared[:4]))

    # 2) rigid body present
    tracks = parse_sb0(style)
    check('rigid snake body (sb0 dash animation) present', tracks is not None)
    check('.snakeBody path element present',
          re.search(r'<path class="snakeBody"', svg) is not None)

    if tracks:
        off, arr = tracks
        # 3) initial length
        l0 = interp(arr, 0.0, 1)
        check('snake starts at 4 blocks (head + 3 body)',
              abs(l0 - (INITIAL_BLOCKS - 1) * CELL) < 0.5, f'{l0:.0f}px')
        # 4) growth +1 block per dot
        steps_bad = []
        for k in range(len(acts)):
            lo = acts[k] + EPS + 0.005
            hi = acts[k + 1] - EPS - 0.005 if k + 1 < len(acts) else 99.99
            t = (lo + hi) / 2 if hi > lo else lo
            l_exp = (INITIAL_BLOCKS - 1 + k + 1) * CELL
            if abs(interp(arr, t, 1) - l_exp) > 0.5:
                steps_bad.append(k)
        check(f'body grows +1 block per dot eaten ({len(acts)} dots)',
              not steps_bad, str(steps_bad[:4]))
        l_end = interp(arr, 100.0, 1)
        check('final length = 4 + all dots eaten',
              abs(l_end - (INITIAL_BLOCKS - 1 + len(acts)) * CELL) < 0.5,
              f'{l_end:.0f}px')
        # rigid follow
        samples = []
        for k in range(len(times)):
            samples.append(times[k])
            if k + 1 < len(times):
                samples.append((times[k] + times[k + 1]) / 2)
        bad_follow = []
        checked = 0
        for t in samples:
            if any(abs(t - a) < EPS + 0.006 for a in acts):
                continue
            checked += 1
            head = arc_at(t)
            l_exp = length_at(t)
            d = interp(off, t, 1)
            l_arr = interp(arr, t, 1)
            front = -d + l_arr
            back = -d
            if abs(front - head) > TOL or abs(back - (head - l_exp)) > TOL:
                bad_follow.append((round(t, 2), round(front - head, 1),
                                   round(back - (head - l_exp), 1)))
        check(f'body follows the head rigidly ({checked} samples)',
              not bad_follow, str(bad_follow[:3]))

    # 5) durations
    def dur(rule):
        m = re.search(r'\.' + rule + r'\{[^}]*?(\d+)ms', style)
        return int(m.group(1)) if m else None

    d_c, d_s, d_b = dur('c'), dur('s'), dur('snakeBody')
    check('cell/head/body loop durations identical and slowed (>49900ms)',
          None not in (d_c, d_s, d_b) and d_c == d_s == d_b and d_c > 49900,
          f'c={d_c} s={d_s} body={d_b}')
    c_rule = re.search(r'\.c\{[^}]*\}', style)
    check('empty grid cells hidden (base .c opacity:0)',
          c_rule is not None and 'opacity:0' in c_rule.group(0))
    d_cnt = dur('snkcnt')
    if d_cnt is not None:
        check('counter duration matches the loop', d_cnt == d_c,
              f'cnt={d_cnt}')

    print('\n  timeline spot-check:')
    for t in (0.5, 5, 20, 40, 60, 80, 95):
        line = f'    t={t:5.1f}%  head_arc={arc_at(t):7.1f}px  '
        line += f'length={length_at(t) / CELL + 1:4.0f} blocks'
        if tracks:
            off, arr = tracks
            line += f'  tail={-interp(off, t, 1):7.1f}px'
        print(line)
    print()
    if failures:
        print(f'VALIDATION FAILED: {len(failures)} check(s) failed.')
        return 1
    print('VALIDATION PASSED - rigid growing snake verified.')
    return 0


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else \
        'output/github-contribution-grid-snake-enhanced.svg'
    sys.exit(run(path))
