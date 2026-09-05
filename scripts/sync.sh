#!/usr/bin/env bash
# One-command sync of dev DATA (Postgres DB + Wagtail media) between a machine and
# DigitalOcean Spaces. Code travels via git; data travels via Spaces. This just
# chains the db/ and media/ scripts so you type one command instead of two.
#
#   scripts/sync.sh up          # dump DB + media, upload to Spaces  (run where data lives)
#   scripts/sync.sh down        # download from Spaces, restore DB + media
#   scripts/sync.sh db-up       # DB only
#   scripts/sync.sh db-down
#   scripts/sync.sh media-up    # media only
#   scripts/sync.sh media-down
#
# Requires AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in the environment or in .env
# (the underlying scripts auto-load .env). See docs/data-sync.md.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

cmd="${1:-}"
case "$cmd" in
  up)
    step "Dumping DB -> Spaces";    "$HERE/db/db_dump_to_spaces.sh"
    step "Archiving media -> Spaces"; "$HERE/media/media_dump_to_spaces.sh"
    step "Upload complete (DB + media)"
    ;;
  down)
    step "Restoring DB <- Spaces";     "$HERE/db/db_restore_from_spaces.sh"
    step "Extracting media <- Spaces"; "$HERE/media/media_restore_from_spaces.sh"
    step "Download complete (DB + media)"
    ;;
  db-up)      "$HERE/db/db_dump_to_spaces.sh" ;;
  db-down)    "$HERE/db/db_restore_from_spaces.sh" ;;
  media-up)   "$HERE/media/media_dump_to_spaces.sh" ;;
  media-down) "$HERE/media/media_restore_from_spaces.sh" ;;
  ""|-h|--help|help)
    grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "unknown command: $cmd" >&2
    echo "usage: scripts/sync.sh {up|down|db-up|db-down|media-up|media-down}" >&2
    exit 2
    ;;
esac
