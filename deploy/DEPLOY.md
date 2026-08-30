# Self-hosted GitHub stats & activity graph

The public `github-readme-stats.vercel.app`, `github-readme-activity-graph.vercel.app`, and
`github-profile-trophy.vercel.app` deployments are **down for everyone**:
`github-readme-stats` returns HTTP 503 (`DEPLOYMENT_PAUSED`) while
`github-readme-activity-graph` and `github-profile-trophy` return HTTP 402
(`DEPLOYMENT_DISABLED`). These are shared demo instances that got paused/disabled for
billing/quotas. You cannot fix that from the README — the standard fix is to **deploy your
own copies** and point the profile README at them.

The source for all three services is vendored here as git submodules under `deploy/`:

| Service | Submodule | Readme card | Runtime token env |
|---|---|---|---|
| GitHub Stats / Top-Langs / Streak | `deploy/github-readme-stats` | Stats, Top Languages | `PAT_1` |
| Contribution Activity Graph | `deploy/github-readme-activity-graph` | Activity Graph | `TOKEN` |
| GitHub Profile Trophies | `deploy/github-profile-trophy` | Trophies | `GITHUB_TOKEN1`/`GITHUB_TOKEN2` (optional) |

> The `streak-stats.demolab.com` card is a separate, still-healthy service and can stay as-is.

## Prerequisites
1. A **Vercel** account (free tier is fine) — https://vercel.com.
2. A **GitHub Personal Access Token** with `repo` + `read:user` scopes.
   Create it: GitHub → Settings → Developer settings → Personal access tokens → Tokens
   (classic). The token is stored in Vercel as an environment variable and is **only used
   server-side**, never exposed to the profile.

## Deploy GitHub Readme Stats
```bash
cd deploy/github-readme-stats

# (optional) ephemeral clone-free deploy if you did not init submodules:
#   vercel deploy --prod --env PAT_1=<token>

vercel deploy --prod \
  --env PAT_1=<GH_PERSONAL_TOKEN>
```
After it finishes, Vercel prints the production URL, e.g. `https://github-readme-stats-xxxx.vercel.app`.
Optionally alias it to something stable:
```bash
vercel alias <deployment-url> github-readme-stats-asif
```
The resulting base URL is used for the **stats card**, **top languages card** and
(optionally) the **streak card** (streak actually still works on the public
`streak-stats.demolab.com`, so you can leave it).

## Deploy GitHub Readme Activity Graph
```bash
cd deploy/github-readme-activity-graph

vercel deploy --prod \
  --env TOKEN=<GH_PERSONAL_TOKEN>
```
Optionally alias it:
```bash
vercel alias <deployment-url> github-readme-activity-graph-asif
```
The resulting base URL is used for the **activity graph** card.

## Deploy GitHub Profile Trophies
Uses the Deno runtime (the repo ships a `vercel.json` configured for it). Tokens are
optional; provide them to avoid hitting unauthenticated rate limits.
```bash
cd deploy/github-profile-trophy

vercel deploy --prod \
  --env GITHUB_TOKEN1=<TOKEN> \
  --env GITHUB_TOKEN2=<OPTIONAL_SECOND_TOKEN>
```
Optionally alias it:
```bash
vercel alias <deployment-url> github-profile-trophy-asif
```
The resulting base URL is used for the **trophies** card.

> **Stopgap:** until you self-host, the README currently points at a working public mirror
> (`github-profile-trophy-orcin-eta.vercel.app`). It renders but is a third-party deployment
> that may go offline at any time — prefer your own instance for reliability.

## Point the README at your self-hosted instances
After your first deploy, replace the placeholder domains in `README.md` with the real
Vercel URLs:

- Stats + Top Languages:  `https://github-readme-stats-asif.vercel.app/api/...`
- Activity Graph:         `https://github-readme-activity-graph-asif.vercel.app/graph?...`
- Trophies:               `https://github-profile-trophy-asif.vercel.app/?...`

You can search the README for the comments that mark these placeholders:

```
<!-- SELFHOST-STATS: replace domain after deploying github-readme-stats -->
<!-- SELFHOST-GRAPH: replace domain after deploying github-readme-activity-graph -->
<!-- SELFHOST-TROPHIES: replace domain after deploying github-profile-trophy -->
```

## Notes
- The repos ship their own `vercel.json`, so no extra build config is needed.
- If the public `streak-stats.demolab.com` ever goes down, deploy
  `github-readme-stats`'s streak endpoint and point the streak card at it too.
- Keep the deployment env vars private. `PAT_1` / `TOKEN` / `GITHUB_TOKEN1` must be set in
  Vercel (Project → Settings → Environment Variables), not committed to the repo.