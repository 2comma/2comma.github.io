#!/usr/bin/env bash
# Documented hook. It is not installed.
#
# Nothing in this repository schedules this file. There is no cron unit, systemd
# unit, or GitHub Action attached to it. The box YNWA deploy entrypoint was not
# located. Gojo's Team Status routine notifies Zen; it does not call this file.
#
# After a real public YNWA artifact exists, or after a sanctioned ReadCanvas
# handoff has been sanitized into a Team Status bundle, a person can run:
#   ./integration-hook.sh ynwa /absolute/path/to/public-ynwa-artifact
#   ./integration-hook.sh team /absolute/path/to/sanitized-team-status-bundle
#
# A non-zero exit must not be treated as a failed Cloudflare deploy.
# This script does not scrape, does not read Canvas, and does not poll.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 2 ]]; then
  cat >&2 <<'EOF'
public-mirrors: integration hook is not installed.
No deploy entrypoint, scheduler, or Canvas reader is wired.
Pass an explicit target and a local artifact path. See README.md.
EOF
  exit 2
fi
exec "$HERE/sync.sh" "$@"
