# Wdrożenie Konta sudomie (Docker)

Konto to wspólne logowanie dla aplikacji rodziny: dostawca OIDC, firmy, role i zaproszenia. Potrzebujesz:
Docker Engine 24+ z Compose v2, 1 GB RAM, domeny i skrzynki nadawczej (SMTP) — bez poczty nie wyślesz zaproszeń
ani resetu hasła.

## 1. Przygotowanie

```sh
cp .env.example .env
python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # DJANGO_SECRET_KEY
deploy/oidc-klucz.sh                                            # klucz podpisujący tokeny (RAZ, nie gub go!)
```

Uzupełnij `.env`: `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` (z https) i dane SMTP (`EMAIL_*`).
Klucz z `deploy/oidc/klucz.pem` jest jedynym sekretem, którego utrata wylogowuje wszystkich — trzymaj go w kopii.

## 2. Start

```sh
docker compose up -d --build
curl -fsS http://127.0.0.1:8097/zdrowie/     # "ok"
docker compose up -d --build                 # (ten sam krok) — obraz czyta klucz z wolumenu montowanego w compose
```

Kontener sam zrobi migracje, tabelę cache i wczyta rejestr produktów z `produkty.json`. Baza leży na wolumenie
`konto_data` (`/data`).

Pierwsze konto (właściciel instalacji):

```sh
docker compose exec app python manage.py createsuperuser
```

Formularz „Załóż konto firmy” (`/rejestracja/`) jest domyślnie wyłączony. Włącz, gdy chcesz, żeby firmy zakładały się
same: `REJESTRACJA_WLACZONA=1` w `.env` i restart. W przeciwnym razie firmy zakładasz w `/serwis/`.

## 3. Podłączenie aplikacji

Każdy produkt to jeden klient OIDC. Rejestrujesz go komendą (sekret wypisuje się raz):

```sh
docker compose exec app python manage.py klient_oidc kalendarz https://kalendarz.example.com/oidc/callback/ > klient.env
```

Wynik (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`) wklejasz do `.env` produktu razem z
`OIDC_ISSUER=https://twoja-domena/o`. Produkt sam zakłada lokalne konta przy pierwszym logowaniu i synchronizuje role.

Integracja serwer–serwer (bez użytkownika) to osobny klient API:

```sh
docker compose exec app python manage.py klient_api <nazwa-klienta>
```

## 4. HTTPS

Kontener słucha na `127.0.0.1:8097` (`HTTP_PORT`). Postaw przed nim reverse proxy (Caddy, nginx, Traefik)
przekazujące `Host`, `X-Forwarded-Proto: https` i `X-Forwarded-For` albo Cloudflare Tunnel
(`docker compose --profile tunnel up -d` z konfiguracją w `deploy/cloudflared/`). Bez nagłówka
`X-Forwarded-Proto` dostaniesz pętlę przekierowań — `DJANGO_SSL_REDIRECT=0` tylko na czas diagnozy.

HSTS ustawiasz `DJANGO_HSTS_SEKUNDY` (domyślnie 300 s). Podnoś do roku dopiero, gdy HTTPS działa bez problemów —
HSTS jest trudny do cofnięcia.

## 5. Poczta

Zaproszenia, potwierdzenia rejestracji i reset hasła idą przez SMTP z `.env`. Sprawdź wysyłkę na własny adres po
pierwszym zaproszeniu. `DEFAULT_FROM_EMAIL` powinien być adresem technicznym (np. `no-reply@`), a odpowiedzi kieruj
do skrzynki obsługi — Konto nie odbiera poczty.

## 6. Kopie zapasowe

```sh
deploy/backup.sh                                  # baza do deploy/backups/
crontab -e                                        # 25 3 * * * /sciezka/deploy/backup.sh
```

Do kopii dołóż `deploy/oidc/klucz.pem` i `.env` — bez klucza wszystkie tokeny i sesje produktów padają.

## 7. Aktualizacja

```sh
git pull && docker compose up -d --build
```

Migracje robią się przy starcie. Przed aktualizacją: kopia z sekcji 6.

## 8. Typowe problemy

| Objaw | Przyczyna |
|---|---|
| `ImproperlyConfigured: Produkcja wymaga OIDC_KLUCZ_PLIK` | brak klucza: uruchom `deploy/oidc-klucz.sh` i zrestartuj |
| produkty odsyłają „nieprawidłowy redirect_uri” | adres w kliencie OIDC musi być identyczny z tym w produkcie (z ukośnikiem na końcu) |
| zaproszenia nie dochodzą | złe dane SMTP albo nadawca odrzucany przez serwer pocztowy — sprawdź log kontenera |
| pętla przekierowań | proxy bez `X-Forwarded-Proto: https` |
| po zmianie klucza wszyscy wylogowani | oczekiwane: tokeny podpisane starym kluczem przestają być ważne |
