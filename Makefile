# Convenience wrappers for syncing dev DATA (Postgres DB + Wagtail media) between a
# machine and DigitalOcean Spaces. Code travels via git; data travels via Spaces.
# These delegate to scripts/sync.sh so behaviour is identical with or without make.
# See docs/data-sync.md for details and prerequisites.
.PHONY: sync-up sync-down db-up db-down media-up media-down help

help: ; @bash scripts/sync.sh help

sync-up:    ; @bash scripts/sync.sh up
sync-down:  ; @bash scripts/sync.sh down
db-up:      ; @bash scripts/sync.sh db-up
db-down:    ; @bash scripts/sync.sh db-down
media-up:   ; @bash scripts/sync.sh media-up
media-down: ; @bash scripts/sync.sh media-down
