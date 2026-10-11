#!/usr/bin/env python3
"""Rotate the GitHub token used by every self-hosted README card.

The four dynamic cards read one GitHub token each. When it expires they all
break at once while still returning HTTP 200 with an error image, so this
script does the whole rotation in one place rather than four ad-hoc commands
per project.

It is deliberately built around two constraints:

* The token is read from a **file**, never from argv or an environment
  variable. argv is world-readable through `ps`, and this token has to end up
  in Vercel's project settings - not in shell history or a process table.
* The value is handed to `vercel env add` on **stdin**, not via `--value`, for
  the same reason.

Usage
-----
    python3 tools/rotate_token.py /path/to/token.txt          # rotate
    python3 tools/rotate_token.py /path/to/token.txt --dry-run

After a successful rotation the old token is dead everywhere, so it is worth
running the same procedure once more if you are ever unsure where a copy
lingered.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCOPE = "asif-286d"

# project name -> the env var that project's app reads
PROJECTS = {
    "github-readme-stats": "PAT_1",
    "github-readme-activity-graph": "TOKEN",
    "github-readme-streak-stats": "TOKEN",
    "github-profile-trophy": "GITHUB_TOKEN1",
}

# Production hostnames, used only for reporting after the redeploy.
HOSTS = {
    "github-readme-stats": "github-readme-stats-eight-zeta-33.vercel.app",
    "github-readme-activity-graph": "github-readme-activity-graph-drab-nu.vercel.app",
    "github-readme-streak-stats": "github-readme-streak-stats-ashy-three.vercel.app",
    "github-profile-trophy": "github-profile-trophy-mauve-nine.vercel.app",
}

TOKEN_PATTERN = re.compile(r"^(ghp_|github_pat_)[A-Za-z0-9_]{20,}$")


def load_token(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        raise SystemExit("token file is empty")
    if not TOKEN_PATTERN.match(raw):
        # Print the shape, never the value.
        hint = raw[:4] + "..." if len(raw) > 4 else raw
        raise SystemExit(
            f"that does not look like a GitHub token (starts {hint!r}). "
            "Expected a classic PAT (ghp_) or fine-grained token (github_pat_)."
        )
    return raw


def run(args, stdin_value=None):
    return subprocess.run(
        args,
        input=stdin_value,
        capture_output=True,
        text=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("token_file", help="file containing the token (not argv)")
    parser.add_argument(
        "--dry-run", action="store_true", help="validate only, change nothing"
    )
    parser.add_argument(
        "--skip-redeploy", action="store_true", help="set env vars but do not redeploy"
    )
    args = parser.parse_args()

    if shutil.which("vercel") is None:
        raise SystemExit("vercel CLI not found on PATH")

    token = load_token(args.token_file)
    print(f"token loaded from {args.token_file} (value not displayed)\n")

    if args.dry_run:
        for project, var in PROJECTS.items():
            print(f"would set {var} on {project}")
        print("\n--dry-run: nothing changed")
        return 0

    failures = []

    for project, var in PROJECTS.items():
        print(f"── {project} ({var})")

        # --force overwrites in place. Using env rm first would open a window in
        # which the variable does not exist at all, and this app treats a
        # missing PAT as "no tokens" rather than "retry later".
        result = run(
            [
                "vercel", "env", "add", var, "production",
                "--project", project,
                "--scope", SCOPE,
                "--force",
                "--sensitive",
                "--yes",
            ],
            stdin_value=token,
        )
        if result.returncode != 0:
            failures.append(f"{project}: setting {var} failed")
            print(f"   FAILED to set {var}\n{result.stderr.strip()[:300]}\n")
            continue
        print(f"   set {var}")

        if args.skip_redeploy:
            continue

        # A redeploy is required: changing an environment variable does not
        # affect an already-running deployment, so without this the old token
        # stays baked into the function and the cards keep failing.
        result = run(
            ["vercel", "redeploy", HOSTS[project], "--scope", SCOPE]
        )
        if result.returncode != 0:
            failures.append(f"{project}: redeploy failed")
            print(f"   FAILED to redeploy\n{result.stderr.strip()[:300]}\n")
            continue
        print(f"   redeployed {HOSTS[project]}")

    print()
    if failures:
        print("FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("All projects rotated.")
    print("Now verify the origins actually recovered (camo may still cache the old image):")
    print("  python3 tools/check_cards.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())