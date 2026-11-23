# Konto sudomie

Jeden login dla narzędzi sudomie (Grafik, Kalendarz przyjęć, HotelAgenda i kolejne):

- **dostawca OIDC** dla aplikacji rodziny (`django-oauth-toolkit`, PKCE, `scope=openid profile email`),
  z introspekcją tokenów dla integracji serwer–serwer,
- **firmy i role** — jedna osoba może pracować w kilku firmach, w każdej z innymi dostępami do aplikacji,
- **zaproszenia** — link jednorazowy (w bazie tylko skrót), osoba ustawia hasło albo dołącza istniejącym kontem,
- **rejestracja firmy** — właściciel zakłada firmę, potwierdza e-mail, wybiera aplikację startową,
- **Moje konto / Zespół** — zmiana danych, haseł, dostępów; historia zmian i dziennik logowań (RODO).

Produkcja: <https://konto.sudomie.pl>.

## Stos

Django 6.1, Inertia.js + React 19 + Vite, django-oauth-toolkit, django-simple-history, SQLite, Docker Compose.

## Uruchomienie lokalnie

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
.venv/bin/python manage.py migrate
.venv/bin/python manage.py wczytaj_produkty   # rejestr produktów z produkty.json
.venv/bin/python manage.py runserver 127.0.0.1:8012
```

Klienta OIDC dla aplikacji zakłada `manage.py klient_oidc` (wypisuje `OIDC_CLIENT_ID`/`SECRET` dla produktu),
klienta API — `manage.py klient_api`. Konfiguracja poczty przez `EMAIL_*` (lokalnie: konsola).

Testy: `.venv/bin/python -m pytest -q tests`.

## Licencja

MIT — plik `LICENSE`. Prawa: Komorowski & Windorpski sp. z o.o.
