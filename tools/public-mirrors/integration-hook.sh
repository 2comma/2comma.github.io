#!/usr/bin/env bash
# Documented hook. It is not installed.
#
# Nothing in this repository schedules this file. There is no cron unit, systemd
# unit, or GitHub Action attached to it. The box YNWA deploy entrypoint was not
# located. Gojo's Team Status routine notifies Zen; it does not call this file.
#
# YNWA does not publish from this file. After a dashboard upload succeeds, Zen runs
# ynwa-dashboard-handoff.sh with the packaged ZIP digest. See README.md.
# Team Status, after a sanitized bundle exists:
#   ./integration-hook.sh team /absolute/path/to/sanitized-team-status-bundle
#
# A non-zero exit must not be treated as a failed Cloudflare deploy.
# This script does not scrape, does not read Canvas, and does not poll.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == "ynwa" ]]; then
  cat >&2 <<EOF
public-mirrors: YNWA is not mirrored from this hook.
The Cloudflare dashboard is the deploy route. This hook does not upload and does not run by itself.
After the dashboard shows the upload succeeded, run:
  PUBLIC_MIRROR_REPO=/path/to/existing-mirror-checkout $HERE/ynwa-dashboard-handoff.sh --zip /workspace/ynwa-deploy.zip --deployment-id DEPLOYMENT_ID --digest SHA256 --confirm-dashboard-success
EOF
  exit 1
fi
if [[ $# -ne 2 ]]; then
  cat >&2 <<'EOF'
public-mirrors: integration hook is not installed.
No deploy entrypoint, scheduler, or Canvas reader is wired.
YNWA uses ynwa-dashboard-handoff.sh only after a confirmed dashboard upload.
Team uses: integration-hook.sh team /path/to/sanitized-bundle
EOF
  exit 2
fi
exec "$HERE/sync.sh" "$@"
