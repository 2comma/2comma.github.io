# Public mirrors for /ynwa/ and /team/

Installable preparation and release tools for two public GitHub Pages paths in `2comma/2comma.github.io`.

| Target | Pages path | Source this tool accepts | Not accepted |
| --- | --- | --- | --- |
| `ynwa` | `/ynwa/` | A public static YNWA deployment directory or zip (the site root of ynwa.twocommanews.com) | TCR/TCT content, Team Canvas, workers, secrets |
| `team` | `/team/` | A sanitized Team Status bundle for canvas `7160075c-3e2e-45e1-9e05-4a2b2a08f087` | Team TwoComma canvas `b7dd82c4-7324-4829-9d67-68ba4fcb7147`, any other page |

`/news/` and `/lfc/` are not targets. This tool never stages them.

The snapshot in this branch is the Nov 5, 2026 public YNWA artifact (homepage byte-matched to the live hub before link rebasing) and the sanitized Team Status export as of Thu Nov 5, 2026, 7:00 AM PT. The Team page repeats that source text. It does not correct stale board rows or claim a later refresh.

## Source preparation and public release

These are separate steps.

1. `prepare.py` reads a local artifact, checks the allowlist, and writes a staging directory. It does not run git and does not contact the network.
2. `release.py` copies that staging directory into a temporary worktree and commits only `ynwa/` or only `team/`. It fetches the branch tip, rebases when another push landed first, and pushes without `--force`. A conflict stops the release.

`sync.sh` runs both. If `PUBLIC_MIRROR_REPO` is unset it prepares and exits 3 without publishing. That is the current box state: the hook is not installed.

## What the Team export accepts

The bundle contains exactly two files:

- `TeamStatus.tsx`, a default `App` function whose JSX imports only `Page`, `Section`, `Rows`, `Table`, `Callout`, and `Text` from `grok/canvas`.
- `README.md` provenance that contains the approved canvas URL and names `/team/` Team Status.

Values must be string, array, and object literals. The page title must stay `Team Status`. An unknown component, unknown prop, comment, spread, extra file, other canvas id, or sensitive identifier aborts the export. Identifiers are not stripped or rewritten. Insurance policy numbers, UPS tracking numbers, email addresses, long numeric ids, and credential assignments are rejected. The words already substituted in the Nov 5 handoff (`the policy`, `the UPS shipment`) are ordinary text and are kept.

The rendered page is static HTML and CSS. It does not load `grok/canvas` or the Cursor canvas host. Section headings, the status table, and row text are in the document so they remain available without that runtime.

## What the YNWA export accepts

Root files use a public static suffix (`.html`, `.css`, `.js`, `.svg`, `.txt`, `.ico`, `.png`, `.webmanifest`). Images may also live in `avatars/` or `icons/`. Hub icons for Read and Trade are public tiles; their sites are not copied. Root-absolute URLs such as `/avatars/gojo.png` become `/ynwa/avatars/gojo.png`. Links to other projects stay on their original hosts, including `https://team.twocommanews.com`, `https://twocommanews.com`, `https://read.twocommanews.com`, `https://trade.twocommanews.com`, and `https://lfc.twocommanews.com`.

`_headers` and `_redirects` are omitted as deploy metadata and named in the prepare output. `_worker.js`, wrangler config, dotfiles other than that metadata, private directories, and path traversal abort the prepare.

## Install on the box later

This directory is the installable artifact. Copy it outside the publishing checkout, for example to `/workspace/jack/public-mirrors/`. Do not add a cron entry, a GitHub Action, or a Cloudflare deploy from this copy. Suggested one-time clone, separate from the TCN and LFC checkouts:

```bash
git clone https://github.com/2comma/2comma.github.io.git /workspace/jack/ynwa-team-mirror/repo
```

Publish authentication is the credential helper or SSH key already configured for that clone. These scripts do not read, store, or print `GH_TOKEN`, `GITHUB_TOKEN`, or `CLOUDFLARE_API_TOKEN`. Do not put a token in the scripts or the remote URL.

```bash
export PUBLIC_MIRROR_REPO=/workspace/jack/ynwa-team-mirror/repo
# optional: PUBLIC_MIRROR_REMOTE (default origin), PUBLIC_MIRROR_BRANCH (default main)
./sync.sh ynwa /absolute/path/to/public-ynwa-artifact
./sync.sh team /absolute/path/to/sanitized-team-status-bundle
```

`integration-hook.sh` is the same call with a usage message when arguments are missing. It exits 2 until someone passes a target and a local path. Wire it only from the real success path, and ignore its exit status there so a mirror failure does not roll back the already-successful deploy:

```bash
/workspace/jack/public-mirrors/integration-hook.sh ynwa "$PUBLIC_YNWA_ARTIFACT" \
  || echo "WARN: GitHub /ynwa mirror failed (deploy unaffected)" >&2
```

## Hooks that are not installed

- YNWA: no deploy entrypoint was found on the box. Updates have been direct static edits and a dashboard zip. Do not point this tool at a guessed path.
- Team Status: Gojo's daily update, about 7 AM PT, notifies Zen after canvas `7160075c-3e2e-45e1-9e05-4a2b2a08f087` saves. The routine does not call this hook. Zen reads that canvas with ReadCanvas, sanitizes the JSX, and only then passes the bundle to `sync.sh team`. Do not scrape `team.twocommanews.com` or the Team TwoComma canvas.
- No polling of GitHub Pages build status is included. A bounded retry applies only to a rejected non-fast-forward git push. TCN and LFC keep their own checkouts; this release uses a separate worktree and does not hard-reset the branch. If both sides edit the same mirror path, the rebase stops and the remote is left as the other push wrote it.

## Checks

From the repository root:

```bash
python3 tools/public-mirrors/test_public_mirrors.py
```

Exit codes from `sync.sh`: `0` published or already current, `1` rejected artifact or failed release, `2` usage, `3` prepared but not published because the checkout is unset.
