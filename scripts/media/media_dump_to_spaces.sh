#!/usr/bin/env bash
# Archive the Wagtail media directory (/app/media in the `web` container, backed by
# the `media_data` volume) and upload it to S3-compatible storage (DigitalOcean
# Spaces) under <prefix>/hall-media-<timestamp>.tar.gz plus a stable
# <prefix>/hall-media-latest.tar.gz pointer.
#
# Run this on the machine that HAS the images (your laptop's compose stack), with
# the stack up. It pairs with media_restore_from_spaces.sh on the other side.
#
# Requires in the environment:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY   (Spaces keys with write access)
# Optional overrides:
#   SPACES_BUCKET (default: AWS_STORAGE_BUCKET_NAME or "sacred")
#   SPACES_PREFIX (default: "archive")
#   AWS_S3_ENDPOINT_URL (your Spaces regional endpoint, e.g. https://<region>.digitaloceanspaces.com)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Load the compose env file so AWS_*/SPACES_* work even if not exported in the shell.
if [ -f "$REPO_ROOT/.env" ]; then set -a; . "$REPO_ROOT/.env"; set +a; fi

# Git Bash on Windows rewrites leading-/ arguments (e.g. /app/...) to
# C:/Program Files/Git/app/... before docker sees them.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

# Pick a working docker invocation (plain for Docker Desktop / docker group,
# passwordless sudo for the nested Cloud Agent VM).
if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo -n docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "ERROR: cannot access the Docker daemon (tried plain and sudo)." >&2
  exit 1
fi
BUCKET="${SPACES_BUCKET:-${AWS_STORAGE_BUCKET_NAME:-sacred}}"
PREFIX="${SPACES_PREFIX:-archive}"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$REPO_ROOT/tmp"
HOST_FILE="$REPO_ROOT/tmp/hall-media-$TS.tar.gz"
CONT_FILE="/app/tmp/hall-media-$TS.tar.gz"  # same file, seen inside the web container

echo "Archiving /app/media ..."
# Stream a gzip tar of the media tree (originals + renditions + documents) to the host.
"${DC[@]}" exec -T web sh -c 'cd /app/media 2>/dev/null && tar czf - . || tar czf - -T /dev/null' > "$HOST_FILE"
echo "  wrote $HOST_FILE ($(du -h "$HOST_FILE" | cut -f1))"

# Upload via the web container's boto3 (no host aws/boto3 needed).
for KEY in "$PREFIX/hall-media-$TS.tar.gz" "$PREFIX/hall-media-latest.tar.gz"; do
  "${DC[@]}" exec -T \
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_S3_ENDPOINT_URL \
    web python /app/scripts/db/s3_transfer.py up --bucket "$BUCKET" --key "$KEY" --file "$CONT_FILE"
done

echo "Done. Latest pointer: s3://$BUCKET/$PREFIX/hall-media-latest.tar.gz"
