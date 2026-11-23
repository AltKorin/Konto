#!/usr/bin/env bash
# Kopiuje projekt na serwer (uruchom na laptopie). Sekrety (.env) nie jadą tą drogą.
# Użycie: deploy/push.sh alias:/opt/kalendarz
set -euo pipefail
target="${1:?Podaj cel, np. konto-prod:/opt/konto}"
cd "$(dirname "$0")/.."
rsync -az --delete --exclude .env --exclude .dev-konta.txt --exclude .venv --exclude .remember --exclude node_modules \
  --exclude frontend/dist --exclude db.sqlite3 --exclude staticfiles --exclude '__pycache__' \
  --exclude deploy/cloudflared --exclude deploy/oidc --exclude deploy/backups \
  ./ "$target/"
echo "Wysłano. Na serwerze: cd ${target#*:} && deploy/deploy.sh"
