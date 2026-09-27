# Self-hosted GitHub README cards

The public `github-readme-stats.vercel.app`, `github-readme-activity-graph.vercel.app`, and
`github-profile-trophy.vercel.app` deployments are **down for everyone**:
`github-readme-stats` returns HTTP 503 (`DEPLOYMENT_PAUSED`) while
`github-readme-activity-graph` and `github-profile-trophy` return HTTP 402
(`DEPLOYMENT_DISABLED`). These are shared demo instances that got paused/disabled for
billing/quotas. You cannot fix that from the README — the fix is to **deploy your own
copies** and point the profile README at them.

The source for all four services is vendored here as git submodules under `deploy/`.
Check them out with:

```bash
git submodule update --init --recursive
```

| Service | Submodule | Readme card | Production URL | Runtime token env |
|---|---|---|---|---|
| GitHub Stats / Top-Langs | `deploy/github-readme-stats` | Stats, Top Languages | `github-readme-stats-eight-zeta-33.vercel.app` | `PAT_1` |
| Contribution Activity Graph | `deploy/github-readme-activity-graph` | Activity Graph | `github-readme-activity-graph-drab-nu.vercel.app` | `TOKEN` |
| GitHub Profile Trophies | `deploy/github-profile-trophy` | Trophies | `github-profile-trophy-mauve-nine.vercel.app` | `GITHUB_TOKEN1` (optional) |
| Commit Streak | `deploy/github-readme-streak-stats` | Commit Streak | `github-readme-streak-stats-ashy-three.vercel.app` | `TOKEN` (required) |

All four Vercel projects live in the **`asif-286d`** scope. The streak card is a **separate
deployment**, not the `github-readme-stats` streak endpoint — it is its own PHP app with
its own project and its own `TOKEN`.

## Prerequisites
1. A **Vercel** account (free tier is fine) — https://vercel.com. The projects below live in
   the **`asif-286d`** scope, so run `vercel` commands with `--scope asif-286d` if your
   default scope is the personal one.
2. A **GitHub Personal Access Token** with `repo` + `read:user` scopes.
   Create it: GitHub → Settings → Developer settings → Personal access tokens → Tokens
   (classic). The token is stored in Vercel as an environment variable and is **only used
   server-side**, never exposed to the profile.
   *Exception:* the Commit Streak service needs **no scopes** — its token exists only to
   authenticate the GraphQL query and lift the rate limit. A separate no-scope token is
   fine for it.

## Deploy GitHub Readme Stats
```bash
cd deploy/github-readme-stats

# (optional) ephemeral clone-free deploy if you did not init submodules:
#   vercel deploy --prod --env PAT_1=<token>

vercel deploy --prod \
  --env PAT_1=<GH_PERSONAL_TOKEN>
```
After it finishes, Vercel prints the production URL, e.g. `https://github-readme-stats-xxxx.vercel.app`.
That hostname is the one the README must point at, so copy it verbatim rather than inventing
an alias. If you do alias it, update the URL in `README.md` in the same change.
```bash
vercel alias <deployment-url> github-readme-stats-asif
```
The resulting base URL is used for the **stats card** and the **top languages card**. The
**streak card** is a different deployment — see [Deploy Commit Streak](#deploy-commit-streak).

## Deploy GitHub Readme Activity Graph
> **Local patch:** the submodule carries a local commit ("Add per-day contribution
> tooltips and total-count title") that appends `• Total: N contributions` to the
> graph title and injects per-day `<title>` hover tooltips into each data point
> (tooltips show when the SVG is opened directly; GitHub's `<img>` embed can't show
> them). The patch is saved at `deploy/patches/activity-graph-contribution-counts.patch`
> — after cloning fresh submodules, apply it with:
> `git -C deploy/github-readme-activity-graph apply ../patches/activity-graph-contribution-counts.patch`

```bash
cd deploy/github-readme-activity-graph

vercel deploy --prod \
  --env TOKEN=<GH_PERSONAL_TOKEN>
```
The resulting base URL is used for the **activity graph** card. The hostname Vercel prints is
the one the README must point at; if you alias it, update `README.md` in the same change.

## Deploy GitHub Profile Trophies
Uses the Deno runtime (the repo ships a `vercel.json` configured for it). Tokens are
optional; provide them to avoid hitting unauthenticated rate limits.
```bash
cd deploy/github-profile-trophy

vercel deploy --prod \
  --env GITHUB_TOKEN1=<TOKEN> \
  --env GITHUB_TOKEN2=<OPTIONAL_SECOND_TOKEN>
```
The resulting base URL is used for the **trophies** card. Same rule as above: use the hostname
Vercel prints, and update `README.md` if you alias it.

> **Stopgap (no longer needed):** the README previously pointed at a public mirror
> (`github-profile-trophy-orcin-eta.vercel.app`) while this was being set up. It now points at
> the self-hosted `github-profile-trophy-mauve-nine.vercel.app`.

## Deploy Commit Streak
> **Local patch:** the submodule carries a local commit that lowers the cache duration from
> 24 hours to 1 hour (see [Caching](#caching-why-the-streak-card-lags) below). The patch is
> saved at `deploy/patches/streak-stats-cache-duration.patch` — after a fresh submodule clone,
> reapply it with:
> `git -C deploy/github-readme-streak-stats apply ../patches/streak-stats-cache-duration.patch`

This is a PHP app (the repo ships a `vercel.json` for the `vercel-php@0.9.0` runtime), so
Vercel installs the Composer dependencies during the build. It **requires** `TOKEN` — without
it `api/index.php` renders an error instead of a card.

```bash
cd deploy/github-readme-streak-stats

# Link to the EXISTING project so the production URL is preserved.
# Skipping this creates a new project and breaks the README's image URL.
vercel link --project github-readme-streak-stats --scope asif-286d

vercel deploy --prod
```

`vercel link` writes a `.env.local` holding a Vercel OIDC token. The submodule's `.gitignore`
ignores `.env*`, so it must never be committed.

## Caching: why the streak card lags
This card is generated live per request, but **three caches sit in front of it**, and the
outermost is the one that bites:

1. `api/cache.php` writes stats to `/tmp/cache` on the lambda (server-side, up to
   `CACHE_DURATION`).
2. `api/index.php` sends `Cache-Control: public, max-age=$cacheSeconds` with the same
   constant, so **browsers and proxies** hold the SVG.
3. **GitHub's camo image proxy** (Fastly) ingests that header and caches the SVG under an
   HMAC of the image URL for the same duration.

The failure mode this causes: camo caches whatever the origin served *at fetch time*, and
`CACHE_DURATION` is also how stale that snapshot is allowed to be. At the default 24h the
card could lag GitHub's contribution graph by **up to 48h** — a snapshot taken while it was
already a day behind, then held another day. That is exactly how it came to read
`Sep 15 - Sep 25 | 11` on the 27th.

Two rules follow:

- **Bump the cache-buster to force a re-fetch.** The streak `src` in `README.md` carries a
  `&v=N` parameter. Camo's cache key is an HMAC of the whole URL, so changing `N` gives a
  cold cache and an immediate fresh fetch. Increment it after any change that must become
  visible *now* rather than at the next TTL expiry.
- **Diagnose from the headers, not the rendered card.** `curl -I` the card and read
  `x-cache`, `age`, `last-modified` and `expires`. `x-cache: HIT` with a large `age` means
  you are looking at a cached copy and the origin is irrelevant; `x-cache: MISS` with
  `age: 0` means you are looking at freshly generated output. To bypass camo entirely, open
  the Vercel URL directly.

Do **not** set `CACHE_DURATION` below ~1h. Upstream exposes `DISABLE_CACHE=true`, but the
app queries the GitHub GraphQL API and a short TTL invites rate limiting.

## Point the README at your self-hosted instances
The profile README is already wired to the four production URLs in the table above. Three of
them are marked by an HTML comment. Note that `SELFHOST-TROPHIES` and `SELFHOST-GRAPH` sit
inside **multi-line** comments, so grep for the marker text rather than a whole tag:

```bash
grep -n "SELFHOST-" README.md
```

| Marker | URL it points at |
|---|---|
| `SELFHOST-STATS:` | `github-readme-stats-eight-zeta-33.vercel.app` |
| `SELFHOST-GRAPH:` | `github-readme-activity-graph-drab-nu.vercel.app` |
| `SELFHOST-TROPHIES:` | `github-profile-trophy-mauve-nine.vercel.app` |

The Commit Streak card has no `SELFHOST-` marker; it is the `github-readme-streak-stats`
entry in the Stats table of `README.md`. Add a marker there if you touch it.

If you ever re-alias a deployment to a different name, update the URL in `README.md` **and**
bump the streak card's `&v=N` in the same commit — otherwise camo keeps serving the old
image under the old URL's cache key.

## Notes
- The repos ship their own `vercel.json`, so no extra build config is needed.
- The Commit Streak card is self-hosted and does **not** depend on the public
  `streak-stats.demolab.com` instance. If you ever need a fallback while redeploying it,
  the `github-readme-stats` app also exposes a `streak` endpoint you can point at instead.
- Keep the deployment env vars private. `PAT_1` / `TOKEN` / `GITHUB_TOKEN1` must be set in
  Vercel (Project → Settings → Environment Variables), not committed to the repo. The
  templates for each are in `deploy/.env.*.example`; copy the values into Vercel by hand.
- Before trusting a redeploy, check the card actually changed — see
  [Caching](#caching-why-the-streak-card-lags). A correct deploy can still look broken
  because camo is serving a pre-deploy snapshot.
