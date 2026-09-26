#!/usr/bin/env python3
"""Verify the profile README's light/dark image wiring.

Run after editing README.md or the generators:

    python3 tools/check_readme_themes.py

Four classes of bug are checked, all of which have bitten this README before:

1. Structural integrity. cmark-gfm (GitHub's own renderer) is the oracle: a raw
   HTML block ends at a blank line, so a stray blank line inside an <h2> used to
   eject the closing tag and leave a heading glued to the next section. If the
   rendered tag counts do not balance, the markup is malformed.
2. Dark-mode regression. Every dark srcset must be a URL that already existed in
   the README before the light theme was added, which proves the change is
   strictly additive for anyone on a dark theme.
3. Orphaned neon. A neon SVG referenced by a bare <img> outside a <picture> is
   invisible on a light page. Icons that legitimately carry no background are
   allow-listed, as are blocks inside HTML comments.
4. Local asset resolution. Every relative path in the rendered HTML must exist
   on disk, so a typo cannot ship a broken image.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
README = os.path.join(ROOT, "README.md")

# Transparent assets that are fine on white because they use a mid-tone color
# that clears WCAG 1.4.11 (3:1 for non-text), or already switch via an in-SVG
# prefers-color-scheme query. Verified by fetching each and checking both the
# color and whether it paints its own background.
ALLOWED_TRANSPARENT = {
    "espressif/E7352C",      # 4.25:1
    "stmicroelectronics",    # dual-color endpoint, /03234B/FFFFFF
    "nxp",                   # dual-color endpoint, /000000/FFFFFF
}


def fail(problems, message):
    problems.append(message)


def render():
    """Render with cmark-gfm --unsafe, the way GitHub renders README HTML."""
    out = subprocess.run(
        ["cmark-gfm", "--unsafe", README],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def strip_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def main():
    problems = []
    html = render()
    visible = strip_comments(html)
    source = open(README, encoding="utf-8").read()

    # --- 1. Structural integrity, judged by cmark-gfm's own output.
    for tag in ("h2", "h3", "p", "details", "picture", "table"):
        opened = len(re.findall(rf"<{tag}[\s>]", visible))
        closed = len(re.findall(rf"</{tag}>", visible))
        if opened != closed:
            fail(problems, f"unbalanced <{tag}>: {opened} open vs {closed} close")

    pics = re.findall(r"<picture>(.*?)</picture>", visible, re.S)
    if not pics:
        fail(problems, "no <picture> elements rendered")
    for i, p in enumerate(pics, 1):
        if len(re.findall(r"<source ", p)) != 1:
            fail(problems, f"picture #{i} does not have exactly one <source>")
        if len(re.findall(r"<img ", p)) != 1:
            fail(problems, f"picture #{i} does not have exactly one <img>")
        if 'media="(prefers-color-scheme: dark)"' not in p:
            fail(problems, f"picture #{i} has no dark-mode <source>")

    # --- 2. Dark-mode regression: every dark srcset predates this change.
    baseline = subprocess.run(
        ["git", "show", "HEAD:README.md"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout
    known = set(re.findall(r'(?:src|srcset)="([^"]+)"', baseline))
    dark = re.findall(r'<source media="\(prefers-color-scheme: dark\)" srcset="([^"]+)"', visible)
    for url in dark:
        if url not in known:
            fail(problems, f"dark srcset is new, not a pre-existing asset: {url}")

    # --- 3. Orphaned neon outside <picture>.
    outside = re.sub(r"<picture>.*?</picture>", "", visible, flags=re.S)
    for m in re.finditer(r'<img[^>]*src="([^"]+)"', outside):
        url = m.group(1)
        if any(token in url for token in ALLOWED_TRANSPARENT):
            continue
        if "output/" in url and ("-glow.svg" in url or "about-glow.svg" in url):
            fail(problems, f"neon asset outside <picture> (invisible in light mode): {url}")
        if re.search(r"simpleicons\.org/[^/]+/(00FF9D|FF7B00)$", url):
            fail(problems, f"low-contrast icon outside <picture>: {url}")

    # --- 4. Local assets must exist.
    for url in set(re.findall(r'(?:src|srcset)="((?!https?:)[^"]+)"', visible)):
        if not os.path.exists(os.path.join(ROOT, url)):
            fail(problems, f"local asset does not exist: {url}")

    # --- Report.
    print(f"rendered <picture> blocks : {len(pics)}")
    print(f"dark srcset refs          : {len(dark)} (all pre-existing: "
          f"{not any('dark srcset is new' in p for p in problems)})")
    light = re.findall(r'src="([^"]*?-light\.svg)"', visible)
    print(f"light <img> refs         : {len(light)}")
    for name in sorted({l.split('/')[-1] for l in light}):
        print(f"    {name}")

    if problems:
        print("\nFAILED:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("\nAll README theme checks passed.")


if __name__ == "__main__":
    main()
