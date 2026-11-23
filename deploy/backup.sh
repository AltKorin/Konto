#!/usr/bin/env bash
# Kopia bazy SQLite (cron na serwerze, np. 03:20). Trzyma 14 dni.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p deploy/backups && chmod 700 deploy/backups
docker compose exec -T app python -c "import sqlite3; s=sqlite3.connect('/data/db.sqlite3'); d=sqlite3.connect('/data/kopia.sqlite3'); s.backup(d); d.close()"
docker compose cp app:/data/kopia.sqlite3 "deploy/backups/db-$(date +%F).sqlite3"
chmod 600 deploy/backups/*.sqlite3
find deploy/backups -name 'db-*.sqlite3' -mtime +14 -delete
