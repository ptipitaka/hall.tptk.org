#!/usr/bin/env bash
# Download the Wagtail media archive from S3-compatible storage (DigitalOcean
# Spaces) and extract it into the `web` container's /app/media (the `media_data`
# volume). Pairs with media_dump_to_spaces.sh.
#
# Usage:
#   scripts/media/media_restore_from_spaces.sh [object-key]
# Default object-key is <prefix>/hall-media-latest.tar.gz.
#
# Run from anywhere in the repo with the compose stack up.
#
# Requires in the environment:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY   (Spaces keys with read access)
# Optional overrides:
#   SPACES_BUCKET (default: AWS_STORAGE_BUCKET_NAME or "sacred")
#   SPACES_PREFIX (default: "archive")
#   AWS_S3_ENDPOINT_URL (your Spaces regional endpoint, e.g. https://<region>.digitaloceanspaces.com)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Load the compose env file so AWS_*/SPACES_* work even if not exported in the shell.
if [ -f "$REPO_ROOT/.env" ]; then set -a; . "$REPO_ROOT/.env"; set +a; fi

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
KEY="${1:-$PREFIX/hall-media-latest.tar.gz}"

mkdir -p "$REPO_ROOT/tmp"
BASENAME="$(basename "$KEY")"
HOST_FILE="$REPO_ROOT/tmp/$BASENAME"
CONT_FILE="/app/tmp/$BASENAME"  # same file, seen inside the web container

echo "Downloading s3://$BUCKET/$KEY ..."
"${DC[@]}" exec -T \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_S3_ENDPOINT_URL \
  web python /app/scripts/db/s3_transfer.py down --bucket "$BUCKET" --key "$KEY" --file "$CONT_FILE"
echo "  saved $HOST_FILE ($(du -h "$HOST_FILE" | cut -f1))"

echo "Extracting into /app/media ..."
"${DC[@]}" exec -T web sh -c "mkdir -p /app/media && tar xzf '$CONT_FILE' -C /app/media && echo '  media files: '\$(find /app/media -type f | wc -l)"
echo "Media restore complete."
