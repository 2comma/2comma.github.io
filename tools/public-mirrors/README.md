# Public mirrors for /ynwa/ and /team/

Installable tools for two public paths on `2comma/2comma.github.io`. Copy this directory anywhere outside the git checkout. It does not need to live inside a repository, and it does not create a clone.

`/news/` and `/lfc/` are not targets. A release commits only `ynwa/` or only `team/` in a temporary worktree of an existing checkout. It does not hard-reset that checkout and does not force-push.

The published `/team/` page is the sanitized Team Status export as of Thu Nov 5, 2026, 7:00 AM PT. Stale board text is unchanged. Team TwoComma is not a target.

## What prepare expects

`prepare.py` only writes a staging directory. It does not publish.

YNWA artifact, one of:

- A directory whose root is the public site: `index.html`, `favicon.svg`, `team-logo.svg`, `avatars/*`, and `icons/*`.
- A zip with those files at the archive root. This is the shape of `/workspace/ynwa-deploy.zip` (21 public files, container SHA256 `a9661e6fac7c9ddb71297db464655201caf942a63f024743387ebfa5747b718c`).
- A directory or zip with exactly one wrapper folder that itself contains `index.html`.

Root-absolute URLs such as `/avatars/gojo.png` are rewritten to `/ynwa/...` only in the staging copy. The canonical dist and the deploy ZIP stay as the dashboard artifact. External links stay on their original hosts, including Team, TwoComma News, Read, Trade, and 1892 Reds. A sibling `README`, `reference-scripts/`, or `production/` file makes the artifact fail. `_worker.js`, wrangler config, dotfiles, private directories, and path traversal fail. `_headers` and `_redirects` are omitted and named in the output.

Team artifact:

- A directory or zip with exactly `TeamStatus.tsx` and `README.md`.
- `README.md` must contain `https://cursor.com/canvas/store-2b9c29d3-0086-4e82-8687-c62137bc8463/7160075c-3e2e-45e1-9e05-4a2b2a08f087` and must name `/team/` Team Status.
- The JSX file is one `grok/canvas` import and a default `App` function. Values are string, array, and object literals. The page title must be `Team Status`.
- A lone `.txt` file is not a Team artifact. `/workspace/public-team-status-20261105.txt` is not in this checkout, so it was not used as an input. Put the sanitized JSX and provenance README in one directory, then pass that directory.

Unknown targets fail. Sensitive identifiers are rejected, not rewritten.

## YNWA canonical workflow

There is no existing automatic YNWA deploy hook. The Cloudflare dashboard, project `ynwa-hub`, remains the deploy route. These commands do not upload and do not crawl.

Historical `/workspace/jack/ynwa-hub/dist/` is absent. Restore it once from the known public ZIP. If that directory already contains anything, restore stops and deletes nothing.

```bash
python3 /path/to/public-mirrors/ynwa_canonical.py restore \
  --zip /workspace/ynwa-deploy.zip \
  --dest /workspace/jack/ynwa-hub/dist
```

That ZIP must still have SHA256 `a9661e6fac7c9ddb71297db464655201caf942a63f024743387ebfa5747b718c`. Any other digest is rejected. Edit the restored files in place for a later update. Packaging reads `ynwa-baseline.txt`: the same 21 paths. Adding a file means editing that manifest first.

```bash
python3 /path/to/public-mirrors/ynwa_canonical.py package \
  --dist /workspace/jack/ynwa-hub/dist \
  --out /workspace/ynwa-deploy.zip
```

Packaging prints `sha256=<digest>`, leaves the dist bytes unchanged, and does not deploy or mirror. Upload that exact ZIP in the dashboard. After the dashboard shows the upload succeeded, copy the deployment id and run:

```bash
PUBLIC_MIRROR_REPO=/path/to/existing-mirror-checkout \
  /path/to/public-mirrors/ynwa-dashboard-handoff.sh \
  --zip /workspace/ynwa-deploy.zip \
  --deployment-id DEPLOYMENT_ID \
  --digest SHA256_PRINTED_BY_PACKAGE \
  --confirm-dashboard-success
```

`PUBLIC_MIRROR_REPO` must already be a git checkout of this repository, such as the checkout already used for the news or LFC mirror. If it is unset or is not a checkout, the handoff records nothing further and does not clone. The handoff re-hashes the ZIP. If the file no longer matches `--digest`, it does not mirror. A failed mirror leaves the confirmation in place. Retry the same ZIP with:

```bash
PUBLIC_MIRROR_REPO=/path/to/existing-mirror-checkout \
  python3 /path/to/public-mirrors/ynwa_canonical.py mirror-confirmed \
  --marker /path/to/public-mirrors/ynwa-dashboard-confirmed.json
```

This hook does not run unless Zen passes `--confirm-dashboard-success` after the dashboard upload. Packaging is not deployment.

## Team handoff

Gojo's Team Status update notifies Zen. Zen reads canvas `7160075c-3e2e-45e1-9e05-4a2b2a08f087` with ReadCanvas, sanitizes, and only then:

```bash
PUBLIC_MIRROR_REPO=/path/to/existing-mirror-checkout \
  /path/to/public-mirrors/sync.sh team /path/to/sanitized-team-status-bundle
```

`sync.sh ynwa` refuses. It is not the YNWA deploy hook.

## Install

```bash
unzip public-mirror-tools.zip -d /workspace/jack
# resulting directory: /workspace/jack/public-mirrors
```

Do not add cron, a GitHub Action, or a Cloudflare token. The scripts do not read `GH_TOKEN`, `GITHUB_TOKEN`, or `CLOUDFLARE_API_TOKEN`.

## Checks

```bash
python3 tools/public-mirrors/test_public_mirrors.py
```

`sync.sh` exit codes: `0` published or already current, `1` rejected, `2` usage, `3` prepared but not published because the checkout is unset. YNWA `sync.sh` is always `1` and tells you to use the dashboard handoff.
