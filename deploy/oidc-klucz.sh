#!/usr/bin/env bash
# Klucz RSA podpisujący tokeny OIDC Konta. Tworzy RAZ — zmiana klucza unieważnia tokeny we wszystkich produktach.
# Na serwerze, w katalogu projektu. Kontener czyta go z /run/oidc/klucz.pem (OIDC_KLUCZ_PLIK).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p deploy/oidc
if [ -f deploy/oidc/klucz.pem ]; then echo "Klucz już jest — nie nadpisuję."; exit 0; fi
( umask 077 && openssl genrsa -out deploy/oidc/klucz.pem 2048 2>/dev/null )
chown -R 1000:1000 deploy/oidc && chmod 500 deploy/oidc && chmod 400 deploy/oidc/klucz.pem   # uid 1000 = app w kontenerze
echo "Gotowe: deploy/oidc/klucz.pem"
