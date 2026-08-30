#!/usr/bin/env python3
"""Add a live "dots eaten" counter to a Platane/snk contribution snake SVG.

The snake SVG animates via CSS @keyframes: every dot flashes to its
contribution color at a specific percentage of the 48.7s loop — that instant
is when the snake eats/passses it. This script collects those instants and
overlays a stack of bare numbers at the RIGHT END of the green progress bar
below the grid. Each number is visible only during its time window, so the
counter ticks 0 -> total in sync with the snake animation and resets each loop.

Usage: python3 tools/add_snake_counter.py <path-to-snake.svg>
"""

import re
import sys


def main(path: str) -> None:
    svg = open(path, encoding="utf-8").read()
    if "snkcnt" in svg:
        print("counter already present, skipping")
        return

    # Each cell keyframe looks like: @keyframes cXX{<pct>%{fill:...}...}
    pcts = sorted(
        float(m) for m in re.findall(r"@keyframes c[a-z0-9]+\{([\d.]+)%\{fill", svg)
    )
    total = len(pcts)
    if total == 0:
        raise SystemExit("no cell keyframes found — is this a snk SVG?")

    # Build CSS: number i is visible in the window (pcts[i-1], pcts[i]]
    css_parts = []
    text_parts = []
    for i in range(total + 1):
        a = 0.0 if i == 0 else pcts[i - 1]
        b = 100.0 if i == total else pcts[i]
        css_parts.append(
            f"@keyframes snkcnt{i}{{0%,{a:.2f}%{{opacity:0}}"
            f"{(a + 0.01) if a < 99.99 else a:.2f}%,{min(b, 99.99):.2f}%{{opacity:1}}"
            f"{min(b + 0.01, 100):.2f}%,100%{{opacity:0}}}}"
        )
        text_parts.append(f'<text class="snkcnt snkcnt{i}">{i}</text>')

    overlay_css = (
        ".snkcnt{font:700 12px 'Fira Code',Consolas,monospace;"
        "text-anchor:end;opacity:0;animation:none 48700ms linear infinite;"
        "fill:#00FF9D;filter:url(#snkcntglow)}"
        + "".join(
            f".snkcnt.snkcnt{i}{{animation-name:snkcnt{i}}}" for i in range(total + 1)
        )
        + "".join(css_parts)
    )

    svg = svg.replace("</style>", overlay_css + "</style>", 1)
    # Right end of the green bar (bar rects end at x~848.6, y=144..156).
    # A dark badge with a neon-green border sits behind the glowing numbers so
    # they stay readable on any background (GitHub light/dark).
    counter = (
        '<defs><filter id="snkcntglow" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        '<g transform="translate(848.6,144)">'
        '<rect x="-40" y="-3" width="40" height="18" rx="4" ry="4" '
        'fill="#000000" stroke="#00FF9D" stroke-width="1"/>'
        + "".join(
            f'<text class="snkcnt snkcnt{i}" x="-6" y="12">{i}</text>'
            for i in range(total + 1)
        )
        + "</g>"
    )
    svg = svg.replace("</svg>", counter + "</svg>", 1)

    open(path, "w", encoding="utf-8").write(svg)
    print(f"counter injected: 0..{total} over {total} dot events -> {path}")


if __name__ == "__main__":
    main(sys.argv[1])
