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

# (slug, terminal command text, glow color, size)
# size: "large" = original 30px (used for dropdown summaries),
#       "small" = compact 18px (used for section headings),
#       "xl" = extra large 36px (for prominent dropdowns)
HEADINGS = [
    ("whoami",    "$ whoami",                    "#00FF9D", "small"),  # matrix green
    ("stats",     "$ ./stats.sh --live",         "#00E5FF", "small"),  # cyan
    ("projects",  "$ ls ./projects/",            "#FF2ED1", "small"),  # magenta
    ("techstack", "$ cat /etc/tech-stack.conf",  "#B388FF", "small"),  # violet
    ("tree",      "$ tree . --dirsfirst",        "#FFB300", "small"),  # gold
    ("trophies",  "$ ./trophies.sh",             "#FFC400", "small"),  # amber
    ("graph",     "$ git log --graph --oneline", "#FF7043", "small"),  # orange
    ("contact",   "$ ./contact.sh --connect",    "#40C4FF", "small"),  # electric blue
    ("exit",      "$ exit 0",                    "#FF5252", "small"),  # red
    ("about",     "$ cat about.txt",             "#00FF9D", "small"),  # matrix green
    ("repo",      "$ ls -la asifahamed-dev/",    "#00E5FF", "small"),  # cyan
]

FONT = "'Fira Code', 'JetBrains Mono', Consolas, 'Courier New', monospace"
SIZES = {
    "large": {"font_size": 30, "char_w": 18, "pad": 36, "height": 90, "blur": 4.5},
    "small": {"font_size": 18, "char_w": 11, "pad": 24, "height": 54, "blur": 3},
    "xl": {"font_size": 36, "char_w": 22, "pad": 42, "height": 105, "blur": 5.5}
}


def make_svg(text: str, color: str, size: str) -> str:
    cfg = SIZES[size]
    fs, cw, pad, h, blur = cfg["font_size"], cfg["char_w"], cfg["pad"], cfg["height"], cfg["blur"]
    prompt, cmd = text.split(" ", 1)
    width = pad * 2 + int(len(text) * cw)
    # Position cursor one character space after the end of the command text
    cursor_x = pad + 26 + int(len(cmd) * cw) + cw
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" width="{width}" height="{h}" style="background-color: #00000000;">
  <defs>
    <filter id="neon" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="{blur}" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <style>
    .prompt {{ font-family: {FONT}; font-size: {fs}px; fill: {color}; opacity: 0.6; }}
    .cmd    {{ font-family: {FONT}; font-size: {fs}px; fill: {color}; font-weight: 700; }}
    .glow   {{ filter: url(#neon); }}
    .cursor {{ animation: blink 1.1s steps(2) infinite; }}
    @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
  </style>

  <text x="{pad}" y="{h // 2 + fs // 2 - 4}" class="prompt">{prompt}</text>
  <text x="{pad + 26}" y="{h // 2 + fs // 2 - 4}" class="cmd glow">{cmd}</text>
  <rect x="{cursor_x}" y="{h // 2 - fs // 2 - 2}" width="14" height="{fs + 4}" rx="2" fill="{color}" class="cursor" />
</svg>
'''


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for slug, text, color, size in HEADINGS:
        path = os.path.normpath(os.path.join(OUT_DIR, f"heading-{slug}-glow.svg"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(make_svg(text, color, size))
        print(f"wrote {path} ({size})")


if __name__ == "__main__":
    main()
