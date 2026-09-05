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

echo "Resetting schema and restoring into $DB_NAME (full replace)..."
# Free any locks held by the app, then wipe and recreate the public schema so the
# dump restores into a clean database (avoids pg_restore --clean dependency-order errors).
"${DC[@]}" exec -T db psql -U "$DB_USER" -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" \
  >/dev/null 2>&1 || true
"${DC[@]}" exec -T db psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO \"$DB_USER\"; GRANT ALL ON SCHEMA public TO public;"
"${DC[@]}" exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges < "$HOST_FILE"
echo "Restore complete."
