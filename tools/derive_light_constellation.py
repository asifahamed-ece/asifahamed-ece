#!/usr/bin/env python3
"""Derive the light-mode twin of assets/domain-constellation.svg.

The constellation is hand-authored and paints 48 sites using only 10 distinct
colors, with no <style> block, so the light variant is a mechanical color
substitution plus four targeted attribute fixes. Doing it with a script rather
than a hand copy keeps the two files from drifting apart.

Why a light variant is needed at all: the dark original paints a neon
constellation (#00FF9D, #00D9FF, #B388FF, ...) on an opaque black canvas. The
neon hues measure 1.33:1 to 2.85:1 against white, well under the 4.5:1 WCAG
wants for text, so on a light page the diagram reads as a black slab with
colored confetti in it.

Substitutions are not enough on their own. Three things also have to change:

  * The spokes sit in a group at opacity 0.6. That was a deliberate "decorative
    geometry is dimmer than text" choice against a black canvas, but a darkened
    hue at 0.6 over white composites down to about 2.6:1, so the group opacity
    is raised to 0.9 (min 4.7:1).
  * Secondary labels sit at opacity 0.9. #0A7D3C at 0.9 over the light card
    composites to 4.14:1, just under the bar, so they are repainted in GitHub's
    muted foreground at full opacity, which is also the semantically right
    choice for secondary text.
  * The background grid is a 0.07-opacity green, which is invisible on white.
    It becomes a solid #D0D7DE, matching GitHub's own light-mode border token.

Usage: python3 tools/derive_light_constellation.py
"""

import os
import re
import sys
import xml.dom.minidom
import xml.parsers.expat

HERE = os.path.dirname(os.path.abspath(__file__))
DARK = os.path.normpath(os.path.join(HERE, "..", "assets", "domain-constellation.svg"))
LIGHT = os.path.normpath(os.path.join(HERE, "..", "assets", "domain-constellation-light.svg"))

# Dark canvas -> GitHub light-mode surface tokens.
CARD_BG = "#F6F8FA"
HUB_BG = "#EDF1F5"
GRID = "#D0D7DE"
MUTED = "#57606A"

# Every distinct color in the dark file, mapped to a >=4.5:1 hue on white.
COLOR_MAP = {
    "#000000": "#FFFFFF",  # page canvas
    "#00140D": CARD_BG,   # domain card fill
    "#001A10": HUB_BG,    # hub fill
    "#00FF9D": "#0A7D3C",  # primary neon green -> readable green
    "#00D9FF": "#0E6E8C",  # cyan
    "#B388FF": "#6D3BC7",  # violet
    "#FF4FD8": "#B31B8C",  # magenta
    "#FF6B35": "#B23A0C",  # orange
    "#FFB000": "#8A5A00",  # gold
    "#4D7CFF": "#2C5FD0",  # blue
}

TEXT_MIN = 4.5
GRAPHIC_MIN = 3.0


def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    r, g, b = linear
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def flatten(fg: str, bg: str, alpha: float) -> str:
    """Effective color of fg at `alpha` opacity over bg, as #rrggbb."""
    f, b = fg.lstrip("#"), bg.lstrip("#")
    mixed = [round(alpha * int(f[i:i + 2], 16) + (1 - alpha) * int(b[i:i + 2], 16)) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(mixed)


def substitute_once(svg: str, pattern: str, replacement: str, expected: int, label: str) -> str:
    """Regex substitution that refuses to run if the dark file's shape changed.

    Without the count assertion, an edit to the dark original would silently
    produce a light file that kept the neon colors, which is precisely the bug
    this script exists to prevent.
    """
    new, n = re.subn(pattern, replacement, svg)
    if n != expected:
        sys.exit(
            f"derive_light_constellation: expected {expected} match(es) for {label}, found {n}.\n"
            f"The dark constellation has changed shape; update this script's patterns."
        )
    return new


def derive(dark_svg: str) -> str:
    out = dark_svg

    # 1. Grid: invisible green wash -> GitHub's light border token.
    out = substitute_once(
        out,
        r'stroke="#00FF9D" stroke-width="1" opacity="0\.07"',
        f'stroke="{GRID}" stroke-width="1" opacity="1"',
        1,
        "background grid",
    )

    # 2. Spoke group opacity: 0.6 composites the darker hues to ~2.6:1.
    out = substitute_once(
        out,
        r'(<g fill="none" stroke-width="2\.6" stroke-linecap="round" )opacity="0\.6"',
        r'\1opacity="0.9"',
        1,
        "spoke group opacity",
    )

    # 3. Secondary labels: repaint muted at full opacity.
    out = substitute_once(
        out,
        r'(<text[^>]*?font-size="14"[^>]*?) opacity="0\.9"',
        rf'\1 fill="{MUTED}"',
        9,
        "secondary labels",
    )

    # 4. The color map itself, longest-first so #000000 cannot shadow #00140D.
    # Counted against the current document, not the original: step 1 already
    # consumed one #00FF9D when it repainted the grid.
    for src in sorted(COLOR_MAP, key=len, reverse=True):
        pattern = re.escape(src) + r'(?![0-9A-Fa-f])'
        out = substitute_once(out, pattern, COLOR_MAP[src], len(re.findall(pattern, out)), f"color map {src}")

    return out


def validate(light_svg: str) -> None:
    """Check every text and graphic color in the derived file against its real backdrop."""
    problems = []
    page = COLOR_MAP["#000000"]

    checks = [
        ("card title", "#0A7D3C", CARD_BG, TEXT_MIN),
        ("card sub-label", MUTED, CARD_BG, TEXT_MIN),
        ("card border", "#0A7D3C", page, GRAPHIC_MIN),
        ("hub title", "#0A7D3C", HUB_BG, TEXT_MIN),
        ("hub label", MUTED, HUB_BG, TEXT_MIN),
        ("hub border", "#0A7D3C", page, GRAPHIC_MIN),
    ]
    for name, fg, bg, minimum in checks:
        ratio = contrast_ratio(fg, bg)
        if ratio < minimum:
            problems.append(f"  {name}: {fg} on {bg} is {ratio:.2f}:1 (needs {minimum}:1)")

    for src, dst in COLOR_MAP.items():
        if src not in ("#000000", "#00140D", "#001A10", "#00FF9D"):
            # Spokes and packets render inside the 0.9-opacity spoke group.
            effective = flatten(dst, page, 0.9)
            ratio = contrast_ratio(effective, page)
            if ratio < GRAPHIC_MIN:
                problems.append(f"  spoke {dst} @0.9 on {page} is {ratio:.2f}:1 (needs {GRAPHIC_MIN}:1)")

    # No neon may survive into the light file.
    for neon in ("#00FF9D", "#00D9FF", "#B388FF", "#FF4FD8", "#FF6B35", "#FFB000", "#4D7CFF"):
        if neon.lower() in light_svg.lower():
            problems.append(f"  neon {neon} survived the color map")

    # Catch malformed output here rather than at render time. The usual way to
    # break an SVG this way is a "--" inside a comment, which is illegal in XML.
    try:
        xml.dom.minidom.parseString(light_svg)
    except xml.parsers.expat.ExpatError as exc:
        problems.append(f"  derived SVG is not well-formed XML: {exc}")

    if problems:
        sys.exit("derive_light_constellation: light variant failed validation:\n" + "\n".join(problems))


def main() -> None:
    with open(DARK, encoding="utf-8") as f:
        dark_svg = f.read()

    light_svg = derive(dark_svg)
    light_svg = light_svg.replace(
        "<!-- Hand-authored profile README asset: embedded-domain constellation with restrained SMIL motion. -->",
        "<!-- Light-mode twin of domain-constellation.svg, generated by\n"
        "     tools/derive_light_constellation.py. Do not edit by hand.\n"
        "     Same geometry and SMIL motion; hues darkened to clear WCAG AA on white. -->",
        1,
    )
    validate(light_svg)

    with open(LIGHT, "w", encoding="utf-8") as f:
        f.write(light_svg)

    print(f"wrote {LIGHT}")
    print(f"  card title    #0A7D3C on {CARD_BG} = {contrast_ratio('#0A7D3C', CARD_BG):.2f}:1")
    print(f"  sub-label     {MUTED} on {CARD_BG} = {contrast_ratio(MUTED, CARD_BG):.2f}:1")
    print(f"  hub title     #0A7D3C on {HUB_BG} = {contrast_ratio('#0A7D3C', HUB_BG):.2f}:1")
    # Surface colors are excluded: the canvas flattens to white-on-white.
    worst = min(
        contrast_ratio(flatten(d, COLOR_MAP["#000000"], 0.9), COLOR_MAP["#000000"])
        for d in COLOR_MAP.values()
        if d not in (COLOR_MAP["#000000"], CARD_BG, HUB_BG)
    )
    print(f"  worst spoke   @0.9 on white = {worst:.2f}:1  (needs {GRAPHIC_MIN}:1)")


if __name__ == "__main__":
    main()
