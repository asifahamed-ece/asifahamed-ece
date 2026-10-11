# Fix Broken README Cards & Self-Host Everything

## Context / Problem
The GitHub profile README at `github.com/asifahamed-ece` renders several broken cards. The four *self-hosted* card services all fail. The user wants ALL cards self-hosted by us for uninterrupted service and fewer failure runs.

Repo is cloned at `/home/shadow/asifahamed-ece`. Vercel CLI is at `/usr/bin/vercel`, already authenticated to scope `asif-286d`.

## Root Cause (verified with evidence)
All four self-hosted services fail because their GitHub credentials are invalid/empty. This is NOT rate limiting and NOT a username problem.

Vercel function logs prove it:
- `github-profile-trophy-mauve-nine.vercel.app`: `Authorization: "bearer "` (token EMPTY), response `{"message":"Bad credentials","status":"401"}`, then `Error: Max retries (2) exceeded.`
- `github-readme-activity-graph-drab-nu.vercel.app`: `Bad credentials` (7x)
- `github-readme-streak-stats-ashy-three.vercel.app`: `"message": "Bad credentials"` (4x)
- `github-readme-stats-eight-zeta-33.vercel.app`: `PAT_1 Failed` (12x)

Env vars all EXIST in Vercel (all "Hidden", "Secret", "Production", "30d ago"), so nothing is unset — the values are wrong/expired/revoked.

Proof it is not the username: `https://github-readme-stats-eight-zeta-33.vercel.app/api?username=torvalds` returns the IDENTICAL 771-byte error SVG. Proof GitHub is healthy: unauthenticated `api.github.com` returns 200 with `x-ratelimit-remaining: 58`. Account is fine: 28 public repos, not suspended.

Why the error text lies — each app catches the 401 and shows its own generic message:
- stats -> "Something went wrong! / Downtime due to GitHub API rate limiting" (thrown by `src/common/retryer.js` as `MAX_RETRY` after all tokens are exhausted; secondary message from `SECONDARY_ERROR_MESSAGES.MAX_RETRY`)
- top-langs -> same 771-byte error card
- activity graph -> "Can't fetch any contribution. Please check your username" (its `catch` in `src/fetcher.ts` returns this string for ANY exception, including a 401)
- streak -> "Failed to retrieve contributions. This is likely a GitHub API issue."
- trophies -> HTTP 404 (the Deno function throws, so Vercel serves `index.html` instead)

## SECURITY ISSUE — do first, before anything else
A live PAT was printed in plaintext in the activity-graph axios error dump
(a classic `ghp_`-prefixed token). It was confirmed already dead (HTTP 401) at
the time of writing, so the exposure is not urgent, but it should still be
revoked at github.com/settings/tokens. The value is deliberately **not**
recorded in this document, and no repository file contains it.

## Phase 1 — Fix the four self-hosted cards
1. Create a **fine-grained PAT, no expiry**, read-only on public repos (decision made by user).
2. Revoke the exposed token above first.
3. Set the new token in all four Vercel projects (existing env var names must be kept):
   - `github-readme-stats` -> `PAT_1`
   - `github-readme-activity-graph` -> `TOKEN`
   - `github-readme-streak-stats` -> `TOKEN`
   - `github-profile-trophy` -> `GITHUB_TOKEN1`
   Commands: `vercel env rm <NAME> --project <P> --scope asif-286d` then `vercel env add <NAME> production --project <P> --scope asif-286d`. (Note: `vercel env ls` requires `--project`, not a positional arg; `--yes` is not a valid flag in CLI 59.16.0.)
4. Redeploy each project so the new env value is baked in: `vercel redeploy <project> --prod --scope asif-286d` (or redeploy from source per `deploy/DEPLOY.md`).
5. Verify each origin directly (bypass camo) returns a real card, not an error SVG.

## Phase 2 — Cache-busting (camo) — REQUIRED or the fix will appear not to work
GitHub's camo image proxy (Fastly) caches card SVGs under an HMAC of the image URL, so a fixed origin can still show the stale error card.
- The streak card already has `&v=3` in `README.md` line 113 — bump it (e.g. `&v=4`) to force a cold camo key.
- The other three have NO cache-buster. Either bump a `&v=N` onto them (requires editing README `src`) or wait out the TTL. Verified camo state at time of investigation: stats `age: 306`, streak `age: 304`, activity-graph `age: 0`, top-langs `age: 368446` (~4.3 days stale — this is why the browser showed a WORKING top-langs card while the origin was broken).
- Diagnose with `curl -I`: `x-cache: HIT` + large `age` = you are looking at camo cache, origin irrelevant.

## Phase 3 — Self-host remaining third-party dependencies
Current third-party deps still in `README.md`:

| Dependency | Count | Lines | Plan |
|---|---|---|---|
| `cdn.simpleicons.org` | 7 | 6,7,344,346,348,371,372 | Vendor static SVG |
| `cdn.jsdelivr.net/gh/devicons/...` | 8 | 342,353,355,357,359,364,366,368 | Vendor static SVG |
| `img.shields.io` badges | 3 | 455,459,463 | Vendor static SVG |
| `Tarikul-Islam-Anik/Animated-Fluent-Emojis` | 19 | many | Vendor as-is (user decision) |
| `readme-typing-svg.demolab.com` | 2 | 17,18 | Self-host the server |
| `komarev.com/ghpvc` | 1 | 483 | Self-host too (user decision) |

Static assets (simpleicons + devicons + shields + emojis): download into `assets/`, commit, repoint `README.md` at
`https://raw.githubusercontent.com/asifahamed-ece/asifahamed-ece/main/assets/<file>`.
Verified all 34 static URLs currently return 200 (19 emoji URLs all verified individually). Total vendoring weight ~4094 KB (~3 MB); user chose **vendor as-is** (no optimization). Largest: Rocket.png 850 KB, Ambulance.png 750 KB, Fire.png 595 KB, Waving Hand.png 586 KB, Penguin.png 567 KB.

Dynamic services:
- `readme-typing-svg`: deploy DenverCoder1/readme-typing-svg into the `asif-286d` scope, repoint both the dark `<source>` (line 17, color `00FF9D`) and light `<img>` (line 18, color `0A7D3C`) variants. Both must move together.
- `komarev/ghpvc`: deploy, set the same fine-grained token. Note this one CAN break again when the token dies — it is the last live-API dependency.

## Phase 4 — Prevent recurrence
- Document the token rotation + redeploy procedure in `deploy/DEPLOY.md` (it already documents self-hosting, caching, and env var names).
- Add a scheduled GitHub Actions health-check workflow that curls all six card origins, checks the response contains real card text (not the error strings), and opens an issue on failure. `.github/workflows/` currently only has `snake.yml`.
- Note: `retryer.js` counts PATs via regex `/PAT_\d*$/` — it only counts `PAT_1`-style names. If you ever add a second token it must be named `PAT_2`, `PAT_3`, etc., to be picked up.

## Constraints / Gotchas discovered
- `github-profile-trophy` uses Deno runtime `vercel-deno@3.1.1` per upstream `vercel.json` (rewrites `/(.*)` -> `/api/$1`). Its 404 is the function throwing, not a routing bug.
- Vercel project `github-readme-stats-asif` (`github-readme-stats-asif-navy.vercel.app`) is a 5th, currently-unused project — README points at `github-readme-stats-eight-zeta-33.vercel.app`. Consider deleting it later.
- The snake SVG (`output/github-contribution-grid-snake-enhanced.svg`) is generated by `.github/workflows/snake.yml` and is healthy — do not touch.
- Repo submodules under `deploy/` are NOT checked out (`git submodule status` shows `-` prefix). Run `git submodule update --init --recursive` before editing service source. Patches live in `deploy/patches/` and must be reapplied.

## Out of scope
- Changing card themes/colors.
- The 16 `github.com/...` links (repo links, not images).