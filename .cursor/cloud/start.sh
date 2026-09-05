#!/usr/bin/env bash
# Cloud Agent per-boot startup: bring the Docker daemon and compose stack up.
# Safe to run repeatedly. Dependency install and image build live in install.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Ensure dockerd is running (starts it if a fresh boot).
source "$REPO_ROOT/.cursor/cloud/dockerd.sh"

if [ ! -f "$REPO_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
fi

echo "Starting compose stack (db + web)..."
sudo docker compose up -d

# Wait for the web service to answer.
for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ || true)"
  if [ "$code" = "200" ]; then echo "web is serving at http://localhost:8000/ (HTTP 200)"; exit 0; fi
  sleep 2
done

echo "web did not reach HTTP 200 in time; recent logs:" >&2
sudo docker compose logs --tail=30 web >&2 || true
exit 1
