#!/usr/bin/env bash
# Cloud Agent one-time environment setup (idempotent).
# Installs Docker Engine, builds the compose image, seeds the database, and
# builds the Vue frontend so a fresh agent boots into a ready dev environment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "Docker + compose already installed"
    return
  fi
  echo "Installing Docker Engine + Compose plugin..."
  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  # fuse-overlayfs ships a conffile prompt; --force-confold keeps it non-interactive.
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq -o Dpkg::Options::=--force-confold \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin fuse-overlayfs
}

install_docker

# Start dockerd (configures storage driver / iptables / socket perms).
source "$REPO_ROOT/.cursor/cloud/dockerd.sh"

# Local dev env file (never overwrite an existing one).
if [ ! -f "$REPO_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "Created .env from .env.example"
fi

echo "Building web image..."
sudo docker compose build web

echo "Seeding stack (migrate + bootstrap_site run via entrypoint)..."
sudo docker compose up -d
# Wait for the web service to answer before finishing install.
for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ || true)"
  if [ "$code" = "200" ]; then echo "web is serving (HTTP 200)"; break; fi
  sleep 2
done

# Optional: restore dev data from Spaces (opt-in). Enable by setting
# RESTORE_DB_FROM_SPACES=1 and providing AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
# (e.g. as Cloud Agent Secrets). Safe no-op otherwise.
if [ "${RESTORE_DB_FROM_SPACES:-0}" = "1" ] && [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  echo "Restoring database from Spaces (RESTORE_DB_FROM_SPACES=1)..."
  bash "$REPO_ROOT/scripts/db/db_restore_from_spaces.sh" \
    || echo "WARN: Spaces restore failed; continuing with the seeded database."
else
  echo "Skipping Spaces DB restore (set RESTORE_DB_FROM_SPACES=1 + AWS creds to enable)."
fi

echo "Building Vue frontend (islands)..."
cd "$REPO_ROOT/frontend"
npm install
npm run build
cd "$REPO_ROOT"

echo "Cloud Agent install complete."
