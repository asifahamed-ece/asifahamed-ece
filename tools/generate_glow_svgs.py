#!/usr/bin/env python3
"""Generate glowing terminal-style heading SVGs for the GitHub profile README.

GitHub strips CSS/style attributes from READMEs, so glow effects must be baked
into SVG images (see output/about-glow.svg for the original example). This
script writes one SVG per heading into output/ using the neon glow filter
(feGaussianBlur + feMerge) with a distinct color per section.

Usage: python3 tools/generate_glow_svgs.py
"""

import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# (slug, terminal command text, glow color)
HEADINGS = [
    ("whoami",    "$ whoami",                    "#00FF9D"),  # matrix green
    ("stats",     "$ ./stats.sh --live",         "#00E5FF"),  # cyan
    ("projects",  "$ ls ./projects/",            "#FF2ED1"),  # magenta
    ("techstack", "$ cat /etc/tech-stack.conf",  "#B388FF"),  # violet
    ("tree",      "$ tree . --dirsfirst",        "#FFB300"),  # gold
    ("trophies",  "$ ./trophies.sh",             "#FFC400"),  # amber
    ("graph",     "$ git log --graph --oneline", "#FF7043"),  # orange
    ("contact",   "$ ./contact.sh --connect",    "#40C4FF"),  # electric blue
    ("exit",      "$ exit 0",                    "#FF5252"),  # red
]

FONT = "'Fira Code', 'JetBrains Mono', Consolas, 'Courier New', monospace"
FONT_SIZE = 30
CHAR_W = 18  # approx monospace advance width at 30px
PAD = 36
HEIGHT = 90


def make_svg(text: str, color: str) -> str:
    prompt, cmd = text.split(" ", 1)
    width = PAD * 2 + int(len(text) * CHAR_W)
    cursor_x = width - PAD - 14
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {HEIGHT}" width="{width}" height="{HEIGHT}" style="background-color: #00000000;">
  <defs>
    <filter id="neon" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="4.5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <style>
    .prompt {{ font-family: {FONT}; font-size: {FONT_SIZE}px; fill: {color}; opacity: 0.6; }}
    .cmd    {{ font-family: {FONT}; font-size: {FONT_SIZE}px; fill: {color}; font-weight: 700; }}
    .glow   {{ filter: url(#neon); }}
    .cursor {{ animation: blink 1.1s steps(1) infinite; }}
    @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
  </style>

  <text x="{PAD}" y="{HEIGHT // 2 + FONT_SIZE // 2 - 4}" class="prompt">{prompt}</text>
  <text x="{PAD + 26}" y="{HEIGHT // 2 + FONT_SIZE // 2 - 4}" class="cmd glow">{cmd}</text>
  <rect x="{cursor_x}" y="{HEIGHT // 2 - FONT_SIZE // 2 - 2}" width="14" height="{FONT_SIZE + 4}" rx="2" fill="{color}" class="cursor" />
</svg>
'''


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for slug, text, color in HEADINGS:
        path = os.path.normpath(os.path.join(OUT_DIR, f"heading-{slug}-glow.svg"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(make_svg(text, color))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
