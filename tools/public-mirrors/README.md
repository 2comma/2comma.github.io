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

The GitHub Pages root is this public hub with the same asset paths as the Cloudflare site (`/favicon.svg`, `/avatars/...`). On that root copy only, the public mirrors are local: Team `/team/` (the sanitized Team Status snapshot, not the private canvas behind `team.twocommanews.com`), TwoComma News `/news/`, and 1892 Reds `/lfc/`. TwoComma Read and TwoComma Trade stay on `https://read.twocommanews.com` and `https://trade.twocommanews.com`. PropRuleWatch and JournalCompare stay on their own sites. The rewrite runs on every root sync. Packaging the Cloudflare ZIP does not rewrite those links. `prepare.py` can still write a separate `/ynwa/`-prefixed staging directory for inspection. That directory is not what gets published. `/ynwa/` on GitHub Pages stays a redirect to `https://2comma.github.io/`. A sibling `README`, `reference-scripts/`, or `production/` file makes the artifact fail. `_worker.js`, wrangler config, dotfiles, private directories, and path traversal fail. `_headers` and `_redirects` are omitted and named in the output.

The five links are not five content mirrors. `/news/` and `/lfc/` are the existing public mirrors. `/team/` is only the sanitized Team Status snapshot for canvas `7160075c-3e2e-45e1-9e05-4a2b2a08f087`. The domain `team.twocommanews.com` redirects to a different private Team TwoComma canvas, and this repository does not mirror that canvas. `/read/` and `/trade/` have no pages here. Inventory on Nov 5 found Read as a private server-side gate returning 401 with noindex, and Trade as the same kind of gate. GitHub's docs say a Pages site is public on the internet even when its repository is private, and that Pages should not be used to send passwords ([publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)). Private Pages visibility is an Enterprise Cloud feature for project sites, not for an organization site such as `2comma.github.io`, and it checks GitHub repository access rather than a site password ([visibility](https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site)). Stripping the worker or adding a client-side password would publish the private content. Read and Trade need a server-backed authenticated route off this Pages origin before any content is mirrored. `sync.sh read` and `sync.sh trade` refuse. No placeholder pages are added.

`encrypted-static/` is a separate research prototype. It encrypts a made-up PNG and PDF with WebCrypto PBKDF2-HMAC-SHA-256 and AES-256-GCM. It is not a mirror, `sync.sh` does not publish it, and it must not be copied to `/read/` or `/trade/`. A real password never belongs in this directory. See `encrypted-static/README.md`.

The news deploy script on the box still mirrors before Cloudflare success, and both the news and LFC mirror scripts reset a checkout and stage broadly. They are not in this repository and are not changed here. This tool locks one checkout and pushes fast-forward only for the paths it owns. Pointing those other scripts at the same lock is a later decision.

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

`PUBLIC_MIRROR_REPO` must already be a git checkout of this repository, such as the checkout already used for the news or LFC mirror. If it is unset or is not a checkout, the handoff records nothing further and does not clone. The handoff re-hashes the ZIP. If the file no longer matches `--digest`, it does not publish. When the digest matches, it copies that public hub onto the repository root. Paths stay root-absolute. The only root paths it may replace or delete are `index.html`, `favicon.svg`, `team-logo.svg`, and image files directly in `avatars/` or `icons/`. Other root files, including `robots.txt` or an extra HTML page, are not owned: an artifact that contains one is rejected, and a sync does not delete one that is already in the checkout. It does not stage `news/`, `lfc/`, `team/`, `tools/`, or the `/ynwa/` redirect. A failed publish leaves the confirmation in place. Retry the same ZIP with:

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
python3 /path/to/public-mirrors/test_public_mirrors.py
node /path/to/public-mirrors/encrypted-static/test_encrypted_static.mjs
```

The suite uses the fixtures shipped in this directory and disposable git repositories. It does not read a parent checkout.

`sync.sh` exit codes: `0` published or already current, `1` rejected, `2` usage, `3` prepared but not published because the checkout is unset. YNWA `sync.sh` is always `1` and tells you to use the dashboard handoff.
