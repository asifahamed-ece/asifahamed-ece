#!/usr/bin/env python3
"""Vendor third-party README assets into assets/ and repoint README.md.

Every card in the profile README is supposed to be self-hosted. The dynamic
cards (stats, trophies, activity graph, streak) live on our own Vercel
deployments. The *static* artwork - brand icons, language icons, contact
badges and the animated emoji - does not need a server at all, but it was
being pulled from four outside CDNs, which means those CDNs could break the
profile at any time.

This script downloads that artwork once, commits it under assets/, and
rewrites README.md to reference it through raw.githubusercontent.com, which is
the same host the repo already uses for its generated SVGs. Result: the README
depends on nothing outside this repository for static images.

The mapping is deterministic, so re-running is a no-op once complete. Pass
--force to re-download everything.

Provenance and licensing for every vendored file is recorded in
assets/README.md, which this script maintains.
"""

import argparse
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
ASSETS = REPO_ROOT / "assets"

RAW_BASE = (
    "https://raw.githubusercontent.com/asifahamed-ece/asifahamed-ece/main/assets"
)

USER_AGENT = "vendor_assets.py (profile README asset vendoring)"


def _slug(text):
    """Lowercase, hyphenate, drop anything that is not filename-safe."""
    text = urllib.parse.unquote(text)
    text = text.replace("%20", " ")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-").lower()


def build_mapping(readme_text):
    """Map every third-party static asset URL to a path under assets/."""
    mapping = {}

    # cdn.simpleicons.org/<slug>/<color>[/<light>]  ->  assets/icons/simple-*.svg
    # The three-segment form is simpleicons' auto light/dark variant; it is
    # kept verbatim in the filename so both forms stay distinguishable.
    for match in re.findall(r"https://cdn\.simpleicons\.org/([^\s\"'<>)]+)", readme_text):
        mapping[f"https://cdn.simpleicons.org/{match}"] = (
            f"icons/simple-{_slug(match)}.svg"
        )

    # cdn.jsdelivr.net/gh/devicons/devicon/icons/<lang>/<name>.svg
    # devicons names files "<lang>/<lang>-original.svg"; the repeated language
    # prefix is dropped so the files read as icons/<lang>.svg.
    for match in re.findall(
        r"https://cdn\.jsdelivr\.net/gh/devicons/devicon/icons/([^\s\"'<>)]+?\.svg)",
        readme_text,
    ):
        stem = _slug(match.removesuffix(".svg"))
        prefix = stem.split("-")[0]
        if stem.startswith(prefix + "-"):
            stem = stem[len(prefix) + 1 :]
        mapping[
            "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/" + match
        ] = f"icons/{stem}.svg"

    # img.shields.io/badge/<Label>-<message>-<color>...
    for match in re.findall(r"https://img\.shields\.io/badge/([^\s\"'<>)]+)", readme_text):
        label = match.split("-")[0].replace("%20", " ")
        mapping[f"https://img.shields.io/badge/{match}"] = f"badges/{_slug(label)}.svg"

    # raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/...
    for match in re.findall(
        r"https://raw\.githubusercontent\.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/(Emojis/[^\s\"'<>)]+?\.png)",
        readme_text,
    ):
        name = match.split("/")[-1]
        mapping[
            "https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/"
            + match
        ] = f"emojis/{_slug(name.removesuffix('.png'))}.png"

    return mapping


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} for {url}")
        payload = response.read()
    if not payload:
        raise RuntimeError(f"empty response for {url}")
    dest.write_bytes(payload)
    return len(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-download even if the file exists"
    )
    parser.add_argument(
        "--skip-emojis",
        action="store_true",
        help=(
            "skip the Animated-Fluent-Emojis PNGs. That repository ships a "
            "'Personal Use Only' licence that reserves rights to Microsoft, so "
            "committing its artwork into a public repository is a redistribution "
            "that licence does not clearly grant."
        ),
    )
    args = parser.parse_args()

    readme_text = README.read_text(encoding="utf-8")
    mapping = build_mapping(readme_text)

    if args.skip_emojis:
        emoji_urls = [
            u for u in mapping if "Animated-Fluent-Emojis" in u
        ]
        for url in emoji_urls:
            del mapping[url]
        if emoji_urls:
            print(
                f"Skipping {len(emoji_urls)} emoji file(s) "
                "(personal-use-only licence, see assets/README.md).\n"
            )

    if not mapping:
        print("No third-party static asset URLs found - nothing to do.")
        return 0

    total_bytes = 0
    fetched = skipped = 0

    for url, rel_path in sorted(mapping.items(), key=lambda kv: kv[1]):
        dest = ASSETS / rel_path
        if dest.exists() and not args.force:
            skipped += 1
            continue
        size = download(url, dest)
        total_bytes += size
        fetched += 1
        print(f"  + {rel_path:52s} {size / 1024:8.1f} KB")

    print(
        f"\nFetched {fetched} file(s), {skipped} already present, "
        f"{total_bytes / 1024:.1f} KB new."
    )

    # Rewrite README: longest URL first so that no replacement clobbers a
    # prefix of another (e.g. the two archlinux colour variants).
    updated = readme_text
    replaced = 0
    for url in sorted(mapping, key=len, reverse=True):
        if url in updated:
            replaced += updated.count(url)
            updated = updated.replace(url, f"{RAW_BASE}/{mapping[url]}")

    if updated != readme_text:
        README.write_text(updated, encoding="utf-8")
        print(f"Repointed {replaced} URL reference(s) in README.md")

    leftover = re.findall(
        r"https://(?:cdn\.simpleicons\.org|cdn\.jsdelivr\.net/gh/devicons|"
        r"img\.shields\.io|Tarikul-Islam-Anik)[^\s\"'<>)]*",
        updated,
    )
    if leftover:
        print("\nWARNING: third-party static URLs still present:", file=sys.stderr)
        for url in sorted(set(leftover)):
            print(f"  {url}", file=sys.stderr)
        return 1

    print("No third-party static asset URLs remain in README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
