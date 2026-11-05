#!/usr/bin/env bash
# Prepare one public mirror and, only when PUBLIC_MIRROR_REPO is set, publish it.
# This file is not scheduled. It does not fetch private sites or accept URLs.
# Source preparation stops before any git write when the publish checkout is unset.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 2 ]]; then
  echo "public-mirrors: usage: sync.sh <ynwa|team> <artifact-path>" >&2
  echo "public-mirrors: the integration hook is not installed. See README.md." >&2
  exit 2
fi
TARGET="$1"
ARTIFACT="$2"
case "$ARTIFACT" in
  http://*|https://*|file://*)
    echo "public-mirrors: ERROR refusing a URL artifact. Pass a local file or directory." >&2
    exit 1
    ;;
esac
if [[ "$TARGET" != "ynwa" && "$TARGET" != "team" ]]; then
  echo "public-mirrors: ERROR unknown target page: $TARGET" >&2
  exit 1
fi
STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT
python3 "$HERE/prepare.py" --target "$TARGET" --artifact "$ARTIFACT" --out "$STAGE/site"
if [[ -z "${PUBLIC_MIRROR_REPO:-}" ]]; then
  echo "public-mirrors: prepared ${TARGET} but PUBLIC_MIRROR_REPO is unset; nothing was published. Future sync hookup is not installed." >&2
  exit 3
fi
args=(--target "$TARGET" --staging "$STAGE/site" --repo "$PUBLIC_MIRROR_REPO")
if [[ -n "${PUBLIC_MIRROR_REMOTE:-}" ]]; then
  args+=(--remote "$PUBLIC_MIRROR_REMOTE")
fi
if [[ -n "${PUBLIC_MIRROR_BRANCH:-}" ]]; then
  args+=(--branch "$PUBLIC_MIRROR_BRANCH")
fi
python3 "$HERE/release.py" "${args[@]}"
