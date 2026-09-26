#!/usr/bin/env python3
"""Generate glowing terminal-style heading SVGs for the GitHub profile README.

GitHub strips CSS/style attributes from READMEs, so glow effects must be baked
into SVG images. This script writes one SVG per heading into output/ using the
neon glow filter (feGaussianBlur + feMerge) with a distinct color per section.

Two themes are emitted per heading:

  dark   heading-<slug>-glow.svg   neon on transparent, glow filter applied
  light  heading-<slug>-light.svg  darkened hue on transparent, no glow

The README selects between them with a <picture> element, because
prefers-color-scheme evaluated *inside* an <img>-loaded SVG is not honoured by
GitHub's mobile renderer (it resolves as light). <picture> is evaluated by the
host page instead, and is the mechanism GitHub documents.

The neon palette is unreadable on a white page (#00FF9D on #FFFFFF is 1.33:1,
WCAG wants 4.5:1), and the glow makes it worse by smearing bright pixels into
the surrounding white and eating the glyph stems. So the light theme darkens
each hue to clear 4.5:1, drops the glow filter entirely, and renders the "$"
prompt in GitHub's muted foreground at full opacity rather than a translucent
neon (translucent dark-on-white would fail too).

Usage: python3 tools/generate_glow_svgs.py
"""

import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# (slug, terminal command text, dark glow color, light fill, light rim, size)
# size: "large" = original 30px (used for dropdown summaries),
#       "small" = compact 18px (used for section headings),
#       "xl" = extra large 36px (for prominent dropdowns)
#
# light fill  carries the text, so it is contrast-checked against #FFFFFF by
#             check_contrast() and must clear 4.5:1.
# light rim   is the neon outline painted around each glyph in the light theme.
#             It only has to be perceptible against white, not accessible,
#             because the fill underneath still carries the contrast. A rim
#             that is the same colour as the fill would be invisible, so each
#             one is a brighter, more chromatic version of its own hue. Pale
#             neon cannot be used: #00FF9D is 1.33:1 on white.
HEADINGS = [
    ("whoami",    "$ whoami",                    "#00FF9D", "#0A7D3C", "#00A86B", "small"),  # matrix green
    ("stats",     "$ ./stats.sh --live",         "#00E5FF", "#0E6E8C", "#0090C8", "small"),  # cyan
    ("projects",  "$ ls ./projects/",            "#FF2ED1", "#B31B8C", "#D42BB0", "small"),  # magenta
    ("techstack", "$ cat /etc/tech-stack.conf",  "#B388FF", "#6D3BC7", "#8B5CF6", "small"),  # violet
    ("tree",      "$ tree . --dirsfirst",        "#FFB300", "#8A5A00", "#C99700", "small"),  # gold
    ("trophies",  "$ ./trophies.sh",             "#FFC400", "#8A5A00", "#C99700", "small"),  # amber
    ("graph",     "$ git log --graph --oneline", "#FF7043", "#B23A0C", "#E0620D", "small"),  # orange
    ("contact",   "$ ./contact.sh --connect",    "#40C4FF", "#0B6E99", "#1195C9", "small"),  # electric blue
    ("exit",      "$ exit 0",                    "#FF5252", "#B3261E", "#E03A24", "small"),  # red
    ("about",     "$ cat about.txt",             "#00FF9D", "#0A7D3C", "#00A86B", "small"),  # matrix green
    ("snake",     "$ ./contrib.sh --graph",      "#00FF9D", "#0A7D3C", "#00A86B", "small"),  # matrix green
    ("repo",      "$ ls -la asifahamed-dev/",    "#00E5FF", "#0E6E8C", "#0090C8", "small"),  # cyan
    ("domains",   "$ ./domains.sh --scan",       "#00FF9D", "#0A7D3C", "#00A86B", "small"),  # matrix green
]

# GitHub's light-mode foreground / muted-foreground / border tokens.
LIGHT_INK = "#1F2328"
LIGHT_MUTED = "#57606A"

# WCAG 2.1 minimum contrast for body text against a white page.
MIN_CONTRAST = 4.5

# The rim is decoration on top of an already-accessible fill, so it only has to
# be visible against white. Below this it disappears into the page.
MIN_RIM_CONTRAST = 2.5

# A rim also has to be brighter than the fill it surrounds, or it does not read
# as a lit edge. Measured as a luminance ratio; the shipped palette sits between
# 1.5x and 2.7x.
MIN_RIM_LIFT = 1.25

# Rim weights. The "$" prompt is a smaller glyph than the command text, so it
# gets a lighter touch; past about 1.4px the outline starts eating the
# letterforms at 18px.
RIM_WIDTH_CMD = 1.2
RIM_WIDTH_PROMPT = 0.9


FONT = "'Fira Code', 'JetBrains Mono', Consolas, 'Courier New', monospace"
SIZES = {
    "large": {"font_size": 30, "char_w": 18, "pad": 36, "height": 90, "blur": 4.5},
    "small": {"font_size": 18, "char_w": 11, "pad": 24, "height": 54, "blur": 3},
    "xl": {"font_size": 36, "char_w": 22, "pad": 42, "height": 105, "blur": 5.5}
}


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance of a #rrggbb color."""
    h = hex_color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    r, g, b = linear
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str = "#FFFFFF") -> float:
    """WCAG 2.1 contrast ratio between two #rrggbb colors."""
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast() -> None:
    """Fail loudly if any light-theme color is unreadable on a white page.

    This is the whole point of the light theme, so it is enforced at generation
    time rather than measured once and forgotten.

    Two different bars apply. The fill is the text, so it must clear 4.5:1. The
    rim is decoration painted around a glyph whose fill is still doing the
    accessibility work, so it only has to stay visible against white, and must
    not be the same colour as its own fill or the outline disappears.
    """
    offenders = []
    for slug, _text, dark, light, rim, _size in HEADINGS:
        for label, color, floor in (
            (f"{slug} fill", light, MIN_CONTRAST),
            (f"{slug} rim", rim, MIN_RIM_CONTRAST),
        ):
            ratio = contrast_ratio(color)
            if ratio < floor:
                offenders.append(f"  {label}: {color} is {ratio:.2f}:1 (needs {floor}:1)")
        if rim.lower() == light.lower():
            offenders.append(f"  {slug} rim {rim} is identical to its fill, so the outline is invisible")
        # A rim only reads as a lit edge if it is brighter than the fill it
        # sits around. Measured as a luminance ratio rather than a contrast
        # ratio, because a rim and its fill are the same hue by design and are
        # meant to be hard to tell apart apart from brightness.
        lf, lr = relative_luminance(light), relative_luminance(rim)
        if lf and lr / lf < MIN_RIM_LIFT:
            offenders.append(
                f"  {slug} rim {rim} is only {lr / lf:.2f}x the luminance of its fill "
                f"{light} (needs {MIN_RIM_LIFT}x) so the outline will not read as lit")
    if offenders:
        raise SystemExit("light theme contrast check failed:\n" + "\n".join(offenders))


def make_svg(text: str, color: str, size: str, theme: str = "dark", rim: str | None = None) -> str:
    cfg = SIZES[size]
    fs, cw, pad, h, blur = cfg["font_size"], cfg["char_w"], cfg["pad"], cfg["height"], cfg["blur"]
    prompt, cmd = text.split(" ", 1)
    width = pad * 2 + int(len(text) * cw)
    # Position cursor one character space after the end of the command text
    cursor_x = pad + 26 + int(len(cmd) * cw) + cw

    if theme == "dark":
        defs = f'''  <defs>
    <filter id="neon" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="{blur}" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>'''
        style = f'''    .prompt {{ font-family: {FONT}; font-size: {fs}px; fill: {color}; opacity: 0.6; }}
    .cmd    {{ font-family: {FONT}; font-size: {fs}px; fill: {color}; font-weight: 700; }}
    .glow   {{ filter: url(#neon); }}
    .cursor {{ animation: blink 1.1s steps(2) infinite; }}
    @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}'''
        cmd_class = "cmd glow"
    else:
        # No filter: on white, a neon halo bleeds into the page and destroys the
        # glyph stems. Instead of a glow, the light theme gets a rim, a stroke
        # around each glyph. paint-order puts the stroke behind the fill so only
        # its outer half shows and the letterform is not eaten. The fill still
        # carries the contrast, so the rim is free to be a brighter, more
        # chromatic version of the same hue. The prompt drops its 0.6 opacity
        # because a translucent dark color over white would not clear 4.5:1.
        rim = rim or color
        defs = ""
        style = f'''    .prompt {{ font-family: {FONT}; font-size: {fs}px; fill: {LIGHT_MUTED}; stroke: {rim}; stroke-width: {RIM_WIDTH_PROMPT}px; paint-order: stroke fill; }}
    .cmd    {{ font-family: {FONT}; font-size: {fs}px; fill: {color}; font-weight: 700; stroke: {rim}; stroke-width: {RIM_WIDTH_CMD}px; paint-order: stroke fill; }}
    .cursor {{ animation: blink 1.1s steps(2) infinite; }}
    @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}'''
        cmd_class = "cmd"

    defs_block = f"\n{defs}\n" if defs else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" width="{width}" height="{h}" style="background-color: #00000000;">{defs_block}
  <style>
{style}
  </style>

  <text x="{pad}" y="{h // 2 + fs // 2 - 4}" class="prompt">{prompt}</text>
  <text x="{pad + 26}" y="{h // 2 + fs // 2 - 4}" class="{cmd_class}">{cmd}</text>
  <rect x="{cursor_x}" y="{h // 2 - fs // 2 - 2}" width="14" height="{fs + 4}" rx="2" fill="{color}" class="cursor" />
</svg>
'''


def main() -> None:
    check_contrast()
    os.makedirs(OUT_DIR, exist_ok=True)
    for slug, text, dark, light, rim, size in HEADINGS:
        for theme, color, suffix in (("dark", dark, "glow"), ("light", light, "light")):
            path = os.path.normpath(os.path.join(OUT_DIR, f"heading-{slug}-{suffix}.svg"))
            with open(path, "w", encoding="utf-8") as f:
                f.write(make_svg(text, color, size, theme, rim))
            note = contrast_ratio(color) if theme == "dark" else f"fill {contrast_ratio(color):.2f}:1, rim {contrast_ratio(rim):.2f}:1"
            print(f"wrote {path} ({theme}, {size}, {note})")


if __name__ == "__main__":
    main()
