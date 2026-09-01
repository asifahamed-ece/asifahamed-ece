#!/usr/bin/env python3
"""Validate the enhanced contribution-snake SVG against the Pac-Man-style model
inspired by https://github.com/abozanona/pacman-contribution-graph.

That reference project models every contribution dot as a discrete fill
timeline (getCellAnimationData): the dot shows its real color until the moving
character eats it, then it is permanently flipped to the empty background and
stays gone for the rest of the cycle. We assert the same guarantees on the
enhanced snake by simulating the CSS @keyframes over the loop:

  * every contribution cell is enhanced and shows its real color at rest;
  * once the snake's tail passes a dot it is eaten and stays gone (never comes
    back until the 0% reset of the next loop);
  * the snake body visibly grows over the loop.

Exit code is non-zero on any failing check so it can be used in CI.

Usage: python3 tools/snake_validator.py [path-to-enhanced-svg]
"""

import re
import sys

# Fill value the generator uses for the snake head (keep in sync with snake_growth_enhancer).
HEAD_FILL = "#00FF9D"


def load_cells(svg_content):
    """Return {cell_id: [(pct, props), ...]} for every @keyframes cX block."""
    style = re.search(r"<style>(.*?)</style>", svg_content, re.DOTALL)
    if not style:
        raise SystemExit("no <style> section found")
    style = style.group(1)

    name_re = re.compile(r"@keyframes (c[0-9a-zA-Z]+)")
    seg_re = re.compile(r"([0-9.]+)%\{([^}]+)\}")

    cells = {}
    i = 0
    while True:
        m = name_re.search(style, i)
        if not m:
            break
        name = m.group(1)
        open_b = style.find("{", m.end())
        j = open_b + 1
        depth = 1
        while j < len(style) and depth > 0:
            if style[j] == "{":
                depth += 1
            elif style[j] == "}":
                depth -= 1
            j += 1
        inner = style[open_b + 1 : j - 1]
        cells[name] = [(float(p), pr) for p, pr in seg_re.findall(inner)]
        i = j
    return cells


def classify(props):
    """Map a keyframe segment's fill/opacity to a logical state."""
    fill_m = re.search(r"fill:([^;]+)", props)
    op_m = re.search(r"opacity:([0-9.]+)", props)
    fill = fill_m.group(1) if fill_m else "?"
    op = float(op_m.group(1)) if op_m else 1.0
    if op == 0:
        return "gone"
    if fill == HEAD_FILL:
        return "head" if op >= 1.0 else "body"
    return "real"


def state_at(cells, t):
    """Return {cell_id: state} at loop time t (percent, 0..100)."""
    out = {}
    for name, segs in cells.items():
        cur = segs[0][1]  # state at 0%
        for p, pr in segs:
            if p <= t:
                cur = pr
        out[name] = classify(cur)
    return out


def run(svg_path):
    svg = open(svg_path, encoding="utf-8").read()
    cells = load_cells(svg)
    names = list(cells)
    total = len(names)
    if total == 0:
        raise SystemExit("no contribution-cell keyframes found — not a snk SVG?")
    print(f"cells parsed: {total}")

    failures = []

    def check(label, ok, detail=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
        if not ok:
            failures.append(label)

    # 1) Every cell is enhanced (has a real-color + gone segment), i.e. it is
    #    not a leftover snk default keyframe.
    unenhanced = []
    for name, segs in cells.items():
        joins = ";".join(pr for _, pr in segs)
        if "opacity:0" not in joins or "var(--c" not in joins:
            unenhanced.append(name)
    check("all cells enhanced (visible real color + eaten/gone)",
          not unenhanced, f"unenhanced: {unenhanced[:5]}")

    # 2) Rest state: at the very start of the loop no dot has been eaten.
    rest = state_at(cells, 0.5)
    check("t=0.5%: all dots visible in real color",
          all(v == "real" for v in rest.values()))

    # 3) Eaten dots stay gone: once a cell reaches 'gone' it never returns to
    #    'real' before the 0% reset of the next loop.
    leaked = []
    for name, segs in cells.items():
        seen_gone = False
        for p, pr in segs:
            s = classify(pr)
            if seen_gone and s == "real" and p > 0:
                leaked.append((name, p))
            if s == "gone":
                seen_gone = True
    check("eaten dots never re-appear within the loop", not leaked, f"leaked: {leaked[:5]}")

    # 4) Snake grows: body count at a late time >= body count at an early time.
    body_early = sum(v == "body" for v in state_at(cells, 5.0).values())
    body_late = sum(v == "body" for v in state_at(cells, 40.0).values())
    check("snake body grows (len at 40% >= len at 5%)",
          body_late >= body_early, f"{body_early} -> {body_late}")

    # 5) Mid-loop there is a mix of still-present + being-eaten + already-gone dots.
    mid = list(state_at(cells, 20.0).values())
    check("mid-loop: real + body + gone coexist (dots eaten while others remain)",
          {"real", "body", "gone"} <= set(mid))

    # 6) Loop ends reusable: everything resets to its real color at 0%.
    check("t=0 resets all dots to real color for the next loop",
          all(v == "real" for v in state_at(cells, 0.0).values()))

    print()
    if failures:
        print(f"VALIDATION FAILED: {len(failures)} check(s) failed.")
        return 1
    print("VALIDATION PASSED — animation matches the Pac-Man eat-and-disappear model.")
    return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "output/github-contribution-grid-snake-enhanced.svg"
    sys.exit(run(path))