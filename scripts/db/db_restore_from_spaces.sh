#!/usr/bin/env bash
# Download a Postgres dump from S3-compatible storage (DigitalOcean Spaces) and
# restore it into the Docker Compose `db` service.
#
# Usage:
#   scripts/db/db_restore_from_spaces.sh [object-key]
# Default object-key is <prefix>/hall-latest.dump.
#
# Run from anywhere in the repo with the compose stack up.
#
# Requires in the environment:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY   (Spaces keys with read access)
# Optional overrides:
#   SPACES_BUCKET (default: AWS_STORAGE_BUCKET_NAME or "sacred")
#   SPACES_PREFIX (default: "archive")
#   AWS_S3_ENDPOINT_URL (default: https://sgp1.digitaloceanspaces.com)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

DC=(docker compose)
BUCKET="${SPACES_BUCKET:-${AWS_STORAGE_BUCKET_NAME:-sacred}}"
PREFIX="${SPACES_PREFIX:-archive}"
DB_USER="${POSTGRES_USER:-hall}"
DB_NAME="${POSTGRES_DB:-hall}"
KEY="${1:-$PREFIX/hall-latest.dump}"

mkdir -p "$REPO_ROOT/tmp"
BASENAME="$(basename "$KEY")"
HOST_FILE="$REPO_ROOT/tmp/$BASENAME"
CONT_FILE="/app/tmp/$BASENAME"  # same file, seen inside the web container

echo "Downloading s3://$BUCKET/$KEY ..."
"${DC[@]}" exec -T \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_S3_ENDPOINT_URL \
  web python /app/scripts/db/s3_transfer.py down --bucket "$BUCKET" --key "$KEY" --file "$CONT_FILE"
echo "  saved $HOST_FILE ($(du -h "$HOST_FILE" | cut -f1))"

echo "Restoring into $DB_NAME (clean)..."
"${DC[@]}" exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" \
  --clean --if-exists --no-owner --no-privileges < "$HOST_FILE"
echo "Restore complete."
