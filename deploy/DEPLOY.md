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
| Readme Typing SVG (header) | deployed from a local clone | Header typing animation | `readme-typing-svg-sandy.vercel.app` | none |

All five Vercel projects live in the **`asif-286d`** scope. The streak card is a **separate
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
> **Local patch:** the submodule carries a local commit ("Fix Invalid date tooltips and add
> the total to the graph title") across four files. It appends `• Total: N contributions` to
> the graph title — the number has to live in the title because GitHub renders README images
> in a non-interactive `<img>` context where the per-day `<title>` tooltips cannot appear.
> Those tooltips only show when the SVG is opened directly in a browser.
>
> The tooltips read from a new `isoDate` field rather than `date`. `fetcher.ts` overwrites
> `date` with the bare day-of-month to label the x-axis, so the obvious
> `moment(day.date)` fed it `"27"` and every point rendered as `Invalid date` — the bug this
> commit fixes. `interface.ts` declares the field and `fetcher.ts` sets it before the
> overwrite. The SVG snapshot in `__test__/__snapshots__/` is updated to match.
>
> The patch is saved at `deploy/patches/activity-graph-contribution-counts.patch` and applies
> cleanly to the pinned commit — after cloning fresh submodules, apply it with:
> `git -C deploy/github-readme-activity-graph apply ../patches/activity-graph-contribution-counts.patch`
>
> Upstream's test suite has one pre-existing failure unrelated to this patch
> (`utils.test.ts` expects `Cache-Control: public, max-age=1800`); verify against that
> baseline rather than expecting a fully green run.

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

## Deploy Readme Typing SVG (header card)
> Production URL: `readme-typing-svg-sandy.vercel.app` — self-hosted, no GitHub token needed.

Source is [DenverCoder1/readme-typing-svg](https://github.com/DenverCoder1/readme-typing-svg),
a PHP app that ships **no `vercel.json`** and documents only a Heroku deployment. Self-hosting
it needs two additions, both of which exist in the deployed copy:

1. **`api/index.php`** — Vercel only treats files under `api/` as Serverless Functions, so
   upstream's `src/index.php` is unreachable on its own. The shim mirrors upstream's
   entrypoint but requires the autoloader via an **absolute `__DIR__` path**. Upstream uses
   the relative `require "../vendor/autoload.php"`, which PHP resolves against the working
   directory and `include_path` — not the including file — so from `api/` it misses the
   project-root `vendor/` and the request dies with a fatal error.
2. **`vercel.json`** — routes every path to that function on the `vercel-php@0.9.0` runtime.

There is also a version-skew trap. The app targets PHP 8.1, but Vercel's `vercel-php` runtime
ships **8.5**, where `curl_close()` is deprecated. With `display_errors` on, those notices
print *before* the controller sets its headers, so the response comes back as `text/html`
with a wall of warnings in front of the SVG. The shim sets `display_errors=0` and drops
`E_DEPRECATED`, which keeps the response a clean SVG. Verify this actually held after any
redeploy — the card looks plausible even while broken:

```bash
curl -s -o /dev/null -w '%{http_type} %{size_download}\n' \
  'https://readme-typing-svg-sandy.vercel.app?lines=hello'
# expect: image/svg|xml 8267
```

Both README variants must be repointed together: the dark `<source>` (`color=00FF9D`) and the
light `<img>` (`color=0A7D3C`) are the same card in two colours.

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

## Token rotation

**This is the single most common reason the cards break.** All four dynamic cards
authenticate to GitHub with one token; when it expires or is revoked, every card
fails at once — while still returning **HTTP 200** with a small error image, so
nothing on the profile looks obviously broken.

The messages the cards display do **not** name the real cause. Each app catches
the underlying `401` and substitutes generic text:

| Card | What it displays | What actually happened |
|---|---|---|
| Stats / Top-Langs | "Something went wrong! Downtime due to GitHub API rate limiting" | `retryer.js` exhausted its token list and threw `MAX_RETRY` on a 401 |
| Activity Graph | "Can't fetch any contribution. Please check your username 😬" | its `catch` returns that string for *any* exception, including a 401 |
| Commit Streak | "Failed to retrieve contributions. This is likely a GitHub API issue." | GraphQL rejected the token |
| Trophies | HTTP 404, image doesn't load | the Deno function threw, so Vercel served `index.html` |

So "rate limiting" here means "the token died", and "check your username" means
"the token died". Confirm with the logs before assuming anything else:

```bash
vercel logs github-readme-stats-eight-zeta-33.vercel.app --scope asif-286d | grep -i 'PAT_1 Failed'
vercel logs github-profile-trophy-mauve-nine.vercel.app  --scope asif-286d | grep -o 'Authorization: "[^"]*"'
```

`Bad credentials` from GitHub, or an empty `Authorization: "bearer "`, is the
signature of an expired/revoked token. `Authorization: "bearer "` with nothing
after it means the env var is set but its value is blank.

### Rotating

Create a **fine-grained** token with no expiry so this cannot silently recur:

1. GitHub → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens** → Generate new token.
2. Resource owner: `asifahamed-ece`. Repository access: **Public repositories
   (read-only)** — the cards only read public data, so no private repo access and
   no write scopes are needed.
3. Permissions: **Account permissions → Metadata: Read-only** (mandatory) and
   **Public Repositories: Read-only**.
4. Expiration: **No expiration**.

Then put the token in a file and run the rotation tool, which sets it on all four
projects and redeploys each one:

```bash
printf '%s' 'THE_TOKEN' > ~/.gh-token && chmod 600 ~/.gh-token
python3 tools/rotate_token.py ~/.gh-token
python3 tools/check_cards.py          # expect 6/6 cards healthy
```

The tool reads the token from the **file** and passes it to `vercel env add` on
**stdin**. Do not pass it as `--value` or in an environment variable: argv is
world-readable through `ps`, and this token has to end up in Vercel's project
settings, not in a process table or shell history. Delete the file afterwards
(`shred -u ~/.gh-token` if you like).

It uses `--force` to overwrite each variable in place rather than
`env rm` followed by `env add`. Removing first opens a window in which the
variable does not exist at all, and `github-readme-stats` treats "no PAT found"
as a hard error rather than a retry — so the gap could cache a fresh error image
into camo.

It also **redeploys automatically**, which is not optional: changing an
environment variable does not affect an already-running deployment. Without a
redeploy the old token stays baked into the function and the cards keep failing,
which is the most likely reason a previous rotation appeared to do nothing.
`vercel redeploy` takes a deployment URL or ID (not a project name) and has no
`--scope`/`--prod` flags.

Finally, bump the cache-busters so camo re-fetches:

```bash
# rewrites every &v=N in README.md to N+1
python3 - <<'PY'
import re, pathlib
p = pathlib.Path("README.md"); t = p.read_text()
p.write_text(re.sub(r"&v=(\d+)", lambda m: f"&v={int(m.group(1)) + 1}", t))
PY
```

> **The token in use right now is a classic PAT with `repo` scope.** That is far
> wider than these cards need — `repo` means full read/write on every repository
> on the account, including private ones. It works, but if it ever leaks it is a
> much bigger problem than the cards being broken. Replace it with a fine-grained
> read-only token as described above; nothing else has to change.

## Detecting a broken card

`.github/workflows/check-cards.yml` runs daily and calls all six card origins
directly, bypassing camo. It asserts on *content* rather than status code —
because a broken card is a legitimate HTTP 200 SVG containing an error message —
and opens a single `readme-cards` issue when something regresses, closing it
again on recovery.

Run the same check locally:

```bash
python3 tools/check_cards.py                    # exits 1 if any card is broken
python3 tools/check_cards.py --report out.txt   # capture the report
```

## Self-hosted static assets

Brand icons, language icons and contact badges are committed under `assets/`
and served from `raw.githubusercontent.com`, so they no longer depend on
`cdn.simpleicons.org`, `cdn.jsdelivr.net` or `img.shields.io`. Refresh them with:

```bash
python3 tools/vendor_assets.py --skip-emojis
```

See `assets/README.md` for provenance and licensing. The `--skip-emojis` flag is
deliberate: the emoji CDN's repository carries a personal-use-only licence, so
its artwork is left upstream rather than redistributed here.

## Profile views counter — deliberately NOT self-hosted

The profile-views badge still points at `komarev.com`. It was trialled as a sixth
self-hosted service (`ghpvc-eta.vercel.app`) and **reverted**, for a reason worth
recording before anyone tries it again.

The service works, but it does not survive on Vercel's Hobby plan:

- The counter is a plain integer in a directory. With `REPOSITORY=file` the data
  lives on the lambda's filesystem; `/tmp` is per-instance, so the count is reset
  to `0` on every cold start or redeploy. Verified: 6 increments, then a redeploy,
  then the badge read `0` again.
- The alternative backend is `REPOSITORY=pdo`, which needs a hosted Postgres.
  There is no database in the `asif-286d` scope, and Vercel's Postgres offering is
  not on Hobby.

So a self-hosted copy would show a permanently wrong number, which is worse than a
third-party one that is merely a dependency. It needs a platform with a durable
filesystem or a database (Fly.io, Railway, Render) to be worth doing.

Two PHP-specific traps, if it is ever revisited:

1. `CounterRepositoryFactory` calls `Dotenv::load()`, which **throws** when no
   `.env` file exists — it does not fall back to real environment variables. And
   `.env` is in the project's `.gitignore`, so Vercel's upload filter drops it by
   default; deploying this app needs a `.vercelignore` that does not exclude it.
   Without it every response is a badge reading "Application environment file is
   missing".
2. The app targets PHP 8.1 while Vercel's `vercel-php` ships 8.5, so dependency
   deprecations (EasySVG) are printed into the body ahead of the SVG unless
   `display_errors` is turned off — same fix as [Readme Typing SVG](#deploy-readme-typing-svg-header-card).

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
- The `github-readme-stats-asif` project is unused; the README points at
  `github-readme-stats-eight-zeta-33.vercel.app`. Safe to delete.
