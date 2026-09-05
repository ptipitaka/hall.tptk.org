#!/usr/bin/env bash
# Shared helper: ensure the Docker daemon is running inside the Cloud Agent VM.
# Cloud Agent VMs are nested containers, so Docker must use the fuse-overlayfs
# storage driver (the kernel overlay driver cannot mount here) and legacy
# iptables. dockerd is launched detached and logged to /tmp/dockerd.log.
set -euo pipefail

DOCKERD_LOG="/var/log/dockerd.log"

configure_daemon() {
  sudo mkdir -p /etc/docker
  # storage-driver fuse-overlayfs + classic (non-containerd) snapshotter is the
  # combination that mounts successfully in the nested VM.
  if [ ! -f /etc/docker/daemon.json ]; then
    printf '%s\n' '{
  "storage-driver": "fuse-overlayfs",
  "features": { "containerd-snapshotter": false }
}' | sudo tee /etc/docker/daemon.json >/dev/null
  fi
  # Nested Docker networking is more reliable with legacy iptables.
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy >/dev/null 2>&1 || true
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy >/dev/null 2>&1 || true
}

ensure_docker_group() {
  sudo groupadd -f docker
  sudo usermod -aG docker "$(id -un)" 2>/dev/null || true
}

start_dockerd() {
  if sudo docker info >/dev/null 2>&1; then
    echo "dockerd already running"
  else
    # Clean up any stale socket/pid from a previous boot before relaunching.
    sudo rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null || true
    # Recreate the log fresh each boot as a root-owned, world-writable file so
    # the redirect never fails on a stale file carried over in a snapshot
    # (regardless of which user's shell opens it).
    sudo rm -f "$DOCKERD_LOG" 2>/dev/null || true
    sudo install -m 0666 /dev/null "$DOCKERD_LOG"
    echo "starting dockerd..."
    sudo bash -c "nohup dockerd >>'$DOCKERD_LOG' 2>&1 &"
    for _ in $(seq 1 30); do
      if sudo docker info >/dev/null 2>&1; then break; fi
      sleep 1
    done
    sudo docker info >/dev/null 2>&1 || { echo "dockerd failed to start; see $DOCKERD_LOG"; tail -20 "$DOCKERD_LOG" || true; exit 1; }
    echo "dockerd is up"
  fi
  # Let the (docker-group) agent user reach the socket without sudo.
  sudo chown root:docker /var/run/docker.sock 2>/dev/null || true
  sudo chmod 660 /var/run/docker.sock 2>/dev/null || true
}

configure_daemon
ensure_docker_group
start_dockerd
