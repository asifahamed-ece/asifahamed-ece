#!/usr/bin/env python3
"""Read and set the rendered size of the domain constellation in README.md.

    python3 tools/constellation_size.py            # show intrinsic size, current setting, valid widths
    python3 tools/constellation_size.py --set 640  # resize, keeping width/height in sync

Why a tool instead of editing the number by hand
-------------------------------------------------
The constellation is the one asset in the README whose displayed size matters
visually, and its size is controlled by the <img> width attribute. Two things
make hand-editing error-prone:

  * width and height must agree. The SVG canvas is 800x722, so a width of 640
    needs a height of 578. Mismatched values make GitHub derive a wrong
    aspect-ratio and the diagram is squashed or stretched.
  * width alone leaves aspect-ratio on "auto", so the page reflows once the
    image finishes loading. Setting both reserves the space up front.

Only the width attribute is usable as a knob. GitHub strips author-supplied
style attributes from rendered markdown, so max-width and width:100% do not
apply, but it injects max-width:100% on images itself, so a fixed pixel width
still shrinks to fit narrow screens. That makes a fixed width the correct
mechanism rather than a compromise.

Widths above the intrinsic 800 would upscale the artwork, so 800 is treated as
the ceiling.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
README = os.path.join(ROOT, "README.md")
SVG = os.path.join(ROOT, "assets", "domain-constellation.svg")

# The <img> tag is located by src so the alt text stays free to be edited or
# shortened without breaking this tool.
IMG_RE = re.compile(r'<img\b[^>]*src="assets/domain-constellation\.svg"[^>]*>')

# Steps offered in the table. Kept as multiples that divide 800 evenly enough
# to land on whole pixel heights.
CANDIDATES = [480, 520, 560, 600, 640, 700, 720, 760, 800]


def intrinsic_size():
    with open(SVG, encoding="utf-8") as f:
        head = f.read(2000)
    m = re.search(r'<svg[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"', head)
    if not m:
        sys.exit(f"constellation_size: could not read width/height from {SVG}")
    return int(m.group(1)), int(m.group(2))


def find_tag(readme):
    m = IMG_RE.search(readme)
    if not m:
        sys.exit("constellation_size: no <img> for assets/domain-constellation.svg in README.md")
    return m


def current(tag):
    w = re.search(r'\bwidth="(\d+)"', tag)
    h = re.search(r'\bheight="(\d+)"', tag)
    return (int(w.group(1)) if w else None, int(h.group(1)) if h else None)


def expected_height(width, iw, ih):
    return round(width * ih / iw)


def set_size(readme, tag, width, iw, ih):
    height = expected_height(width, iw, ih)
    new = re.sub(r'\s*\bwidth="\d+"', "", tag)
    new = re.sub(r'\s*\bheight="\d+"', "", new)
    # Insert straight after the src attribute so the two numbers sit together
    # and are the first thing you see when searching for the asset name.
    new = new.replace(
        'src="assets/domain-constellation.svg"',
        f'src="assets/domain-constellation.svg" width="{width}" height="{height}"',
        1,
    )
    return readme.replace(tag, new, 1), height


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", type=int, metavar="WIDTH",
                    help="resize the constellation and update width/height together")
    args = ap.parse_args()

    iw, ih = intrinsic_size()
    with open(README, encoding="utf-8") as f:
        readme = f.read()
    tag = find_tag(readme).group(0)
    cur_w, cur_h = current(tag)

    if args.set is not None:
        if not (240 <= args.set <= iw):
            sys.exit(f"constellation_size: width must be 240..{iw} (intrinsic canvas width), got {args.set}")
        new_readme, h = set_size(readme, tag, args.set, iw, ih)
        with open(README, "w", encoding="utf-8") as f:
            f.write(new_readme)
        print(f"set constellation to {args.set}x{h} (native canvas {iw}x{ih})")
        return

    print(f"intrinsic canvas : {iw}x{ih}")
    print(f"current setting  : {cur_w or '(unset)'}x{cur_h or '(unset)'}")
    print()
    print("  %-8s %-8s %s" % ("WIDTH", "HEIGHT", ""))
    for c in CANDIDATES:
        h = expected_height(c, iw, ih)
        marks = []
        if c == iw:
            marks.append("native canvas")
        if c == cur_w:
            marks.append("current")
        print("  %-8d %-8d %s" % (c, h, ", ".join(marks)))

    print()
    problems = []
    if cur_w is None:
        problems.append("no width attribute; the constellation renders at its intrinsic 800px")
    if cur_w and cur_w > iw:
        problems.append(f"width {cur_w} exceeds the intrinsic {iw}, which upscales the artwork")
    if cur_w and cur_h is None:
        problems.append("height is unset, so aspect-ratio stays auto and the page reflows on load")
    elif cur_w and cur_h:
        want = expected_height(cur_w, iw, ih)
        if abs(cur_h - want) > 1:
            problems.append(f"height {cur_h} does not match width {cur_w}; expected {want} for the {iw}x{ih} canvas")

    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("size setting is consistent.")


if __name__ == "__main__":
    main()
