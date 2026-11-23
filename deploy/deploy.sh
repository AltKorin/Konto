#!/usr/bin/env bash
# Buduje i uruchamia produkcję (na serwerze, w katalogu projektu).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Brak .env — skopiuj deploy/env.production.example do .env i uzupełnij."; exit 1; }
if grep -qE 'replace-with|example\.pl' .env; then echo "W .env zostały wartości z szablonu:"; grep -nE 'replace-with|example\.pl' .env; exit 1; fi
profile=(); [ -f deploy/cloudflared/config.yml ] && profile=(--profile tunnel)
docker compose "${profile[@]}" build
docker compose "${profile[@]}" up -d
for _ in $(seq 1 40); do [ "$(docker compose ps app --format '{{.Health}}')" = healthy ] && break; sleep 3; done
[ "$(docker compose ps app --format '{{.Health}}')" = healthy ] || { docker compose logs --tail 50 app; exit 1; }
docker compose exec -T app python manage.py check --deploy --fail-level ERROR
docker compose ps
echo "Gotowe. Konto dla klienta: docker compose exec app python manage.py createsuperuser."
