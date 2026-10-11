#!/usr/bin/env python3
"""Health-check every dynamic card behind the profile README.

Why this exists
---------------
The cards are self-hosted, so a third-party outage can no longer take them down.
The trade is that they now fail for a reason of our own making: the GitHub token
behind them expires or is revoked, and the card renders an *error* image with
HTTP 200. Nothing on the profile page looks "missing" - it looks like a card
with a message in it - so the breakage is easy to miss.

The failure messages are also actively misleading. Each upstream app catches the
underlying 401 and substitutes its own generic text, so the same dead token is
reported as:

    stats / top-langs   "Something went wrong! Downtime due to GitHub API
                         rate limiting"          (actually MAX_RETRY on a 401)
    activity graph      "Can't fetch any
                         contribution. Please check your username"
                                             (any exception, including a 401)
    streak stats        "Failed to retrieve contributions. This is likely a
                         GitHub API issue."
    profile trophy      HTTP 404                (the function throws, so Vercel
                                                  serves index.html instead)

This script therefore asserts on *content*, not on status code: a healthy card
contains real data, a broken one contains one of the strings above.

It also deliberately calls the Vercel origins rather than the camo URLs GitHub
renders the README through. Camo caches card images under an HMAC of the source
URL and will happily keep serving a broken image for hours, which would make
this check report "healthy" long after the card stopped working.

Usage
-----
    python3 tools/check_cards.py                    # check, print report, exit 1 on failure
    python3 tools/check_cards.py --report FILE      # also write the report to FILE
    python3 tools/check_cards.py --github-output F  # always exit 0, write job outputs
"""

import argparse
import sys
import urllib.error
import urllib.request

TIMEOUT = 30
USER_AGENT = "check_cards.py (README card health check)"

# (label, url, one of these substrings means the card is broken)
CARDS = [
    (
        "stats",
        "https://github-readme-stats-eight-zeta-33.vercel.app/api"
        "?username=asifahamed-ece&show_icons=true&theme=radical&hide_border=true"
        "&bg_color=000000&title_color=00FF9D&icon_color=00FF9D&text_color=CCCCCC",
        ["Something went wrong", "No GitHub API tokens found", "Could not resolve"],
    ),
    (
        "top-langs",
        "https://github-readme-stats-eight-zeta-33.vercel.app/api/top-langs/"
        "?username=asifahamed-ece&layout=compact&theme=radical&hide_border=true"
        "&bg_color=000000&title_color=00FF9D&text_color=CCCCCC",
        ["Something went wrong", "No GitHub API tokens found"],
    ),
    (
        "activity-graph",
        "https://github-readme-activity-graph-drab-nu.vercel.app/graph"
        "?username=asifahamed-ece&theme=react-dark&bg_color=000000&color=00FF9D"
        "&line=00FF9D&point=FFFFFF&area=true&hide_border=true",
        ["Can't fetch any contribution", "rate limit exceeded", "Invalid date"],
    ),
    (
        "streak",
        "https://github-readme-streak-stats-ashy-three.vercel.app"
        "?user=asifahamed-ece&theme=radical&hide_border=true&background=000000"
        "&stroke=00FF9D&ring=00FF9D&fire=00FF9D",
        ["Failed to retrieve contributions", "can't fetch any", "Error"],
    ),
    (
        "trophies",
        "https://github-profile-trophy-mauve-nine.vercel.app/"
        "?username=asifahamed-ece&theme=radical&column=7",
        [],  # any HTML at all means the Deno function threw and index.html leaked
    ),
    (
        "typing-header",
        "https://readme-typing-svg-sandy.vercel.app"
        "?font=Fira+Code&size=28&duration=4000&pause=1000&color=00FF9D"
        "&background=00000000&center=true&vCenter=true&width=800"
        "&lines=asifahamed-ece;Embedded+Systems+Developer",
        # This app renders PHP notices into the body when the runtime is newer
        # than the PHP it targets, so a leading "<br />" is the failure mode.
        ["<br />", "Fatal error", "Deprecated:"],
    ),
]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def check(label, url, bad_markers):
    """Return (ok, detail) for one card origin."""
    try:
        status, content_type, body = fetch(url)
    except urllib.error.HTTPError as error:
        return False, f"HTTP {error.code} {error.reason}"
    except Exception as error:  # noqa: BLE001 - any failure is a failed card
        return False, f"{type(error).__name__}: {error}"

    text = body.decode("utf-8", "replace")

    # A card must be an SVG. The trophies service 404s with the project's own
    # index.html when its function throws, which is how that failure presents.
    if "svg" not in content_type.lower():
        return False, f"expected an SVG, got {content_type or 'unknown'}"

    for marker in bad_markers:
        if marker.lower() in text.lower():
            return False, f"error card rendered: {marker!r}"

    # Look for an <svg> element anywhere rather than at the very start: some
    # generators (readme-typing-svg) emit a leading HTML comment or whitespace,
    # and the broken-stats card is itself a small SVG that would satisfy a
    # naive content-type check.
    if "<svg" not in text.lower():
        return False, "response contains no <svg> element"

    return True, f"{status}, {len(body)} bytes"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", metavar="PATH", help="also write the report here")
    parser.add_argument(
        "--github-output",
        metavar="PATH",
        help=(
            "append `failed=` and a multiline `report=` to this file "
            "(GitHub Actions $GITHUB_OUTPUT) and always exit 0, so a broken "
            "card does not abort the job before the reporting steps run"
        ),
    )
    args = parser.parse_args()

    lines = ["README card health check", ""]
    failed = 0

    for label, url, bad_markers in CARDS:
        ok, detail = check(label, url, bad_markers)
        lines.append(f"{'PASS' if ok else 'FAIL'}  {label:15s} {detail}")
        if not ok:
            failed += 1

    lines.append("")
    lines.append(f"{len(CARDS) - failed}/{len(CARDS)} cards healthy")

    if failed:
        lines.append("")
        lines.append(
            "A card reporting a GitHub API error here almost always means the "
            "token"
        )
        lines.append(
            "on its Vercel project is expired or revoked, not that GitHub is "
            "rate"
        )
        lines.append(
            "limiting. Confirm with `vercel logs <url> --scope asif-286d` and "
            "look for"
        )
        lines.append('`Bad credentials` or `Authorization: "bearer "`.')

    report = "\n".join(lines)
    print(report)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(report + "\n")

    if args.github_output:
        # GITHUB_OUTPUT uses a heredoc-style block for multiline values.
        delimiter = "ghadelimiter_check_cards"
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"failed={'true' if failed else 'false'}\n")
            handle.write(f"report<<{delimiter}\n{report}\n{delimiter}\n")
        return 0

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
