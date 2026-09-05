#!/usr/bin/env bash
# Dump the Postgres database from the Docker Compose `db` service and upload it to
# S3-compatible storage (DigitalOcean Spaces) under <prefix>/hall-<timestamp>.dump
# plus a stable <prefix>/hall-latest.dump pointer.
#
# Run from anywhere in the repo, on a machine where the compose stack is up
# (works the same on your laptop and in the Cloud Agent).
#
# Requires in the environment:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY   (Spaces keys with write access)
# Optional overrides:
#   SPACES_BUCKET (default: AWS_STORAGE_BUCKET_NAME or "sacred")
#   SPACES_PREFIX (default: "archive")
#   AWS_S3_ENDPOINT_URL (default: https://sgp1.digitaloceanspaces.com)
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
DB_USER="${POSTGRES_USER:-hall}"
DB_NAME="${POSTGRES_DB:-hall}"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$REPO_ROOT/tmp"
HOST_FILE="$REPO_ROOT/tmp/hall-$TS.dump"
CONT_FILE="/app/tmp/hall-$TS.dump"  # same file, seen inside the web container (repo is bind-mounted at /app)

echo "Dumping $DB_NAME (custom format)..."
"${DC[@]}" exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$HOST_FILE"
echo "  wrote $HOST_FILE ($(du -h "$HOST_FILE" | cut -f1))"

# Upload via the web container's boto3 (no host aws/boto3 needed).
for KEY in "$PREFIX/hall-$TS.dump" "$PREFIX/hall-latest.dump"; do
  "${DC[@]}" exec -T \
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_S3_ENDPOINT_URL \
    web python /app/scripts/db/s3_transfer.py up --bucket "$BUCKET" --key "$KEY" --file "$CONT_FILE"
done

echo "Done. Latest pointer: s3://$BUCKET/$PREFIX/hall-latest.dump"
