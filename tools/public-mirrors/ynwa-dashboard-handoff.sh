#!/usr/bin/env bash
# Post-dashboard-success handoff for YNWA. Not installed as a scheduler.
#
# The Cloudflare dashboard is still the deploy route. This script does not
# upload, crawl, or create a repository checkout. Run it only after the dashboard shows
# that the ZIP from `ynwa_canonical.py package` was accepted.
#
#   PUBLIC_MIRROR_REPO=/path/to/existing-mirror-checkout \
#     ./ynwa-dashboard-handoff.sh \
#     --zip /workspace/ynwa-deploy.zip \
#     --deployment-id DEPLOYMENT_ID \
#     --digest SHA256_PRINTED_BY_PACKAGE \
#     --confirm-dashboard-success
#
# If the mirror step fails, the confirmation remains. Retry with the same ZIP:
#   PUBLIC_MIRROR_REPO=... python3 ynwa_canonical.py mirror-confirmed --marker MARKER
# A ZIP whose digest no longer matches the confirmation is rejected.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MARKER="${YNWA_CONFIRMATION_MARKER:-$HERE/ynwa-dashboard-confirmed.json}"
exec python3 "$HERE/ynwa_canonical.py" handoff --marker "$MARKER" "$@"
