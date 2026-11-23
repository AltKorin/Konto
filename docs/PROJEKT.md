---
status: projekt
data: 2026-11-20
openproject: https://projekty.sudomie.pl/projects/konto/work_packages
---
# Konto sudomie — jeden login dla całego pakietu

## Cel
Jedno konto (login + hasło) do wszystkich produktów: **Grafik, Kalendarz przyjęć, Grupy, FoodCost, InnDesk, HotelAgenda**
(i kolejnych). Właściciel firmy w jednym miejscu widzi i ustawia, kto ma dostęp do którego produktu i w jakiej roli.
Produkty rozmawiają ze sobą przez API z tokenami wydanymi przez Konto.

Decyzja (2026-11-20, OpenProject #753): **własna usługa** `konto.sudomie.pl` (Django 6.1 + django-oauth-toolkit),
nie Authentik/Keycloak — panel „zespół i dostępy” dla klienta i tak musi być nasz (CLAUDE.md: klient nie uczy się
narzędzi), a gotowy IdP to dodatkowa infrastruktura (Postgres + Redis + ~1,5 GB) z technicznym panelem.
Bez tymczasowego „logowania przez Grafik” — od razu Konto.

## Architektura
```
               konto.sudomie.pl  (dostawca OIDC + panel firmy)
              /     |      |       |        \         \
         Grafik  Kalendarz Grupy  FoodCost  InnDesk  HotelAgenda   ← klienci OIDC (paczka core_sso)
              \______________ API z tokenem aplikacji ___________/  (client credentials od Konta)
```
- **Konto** = jedyne miejsce z hasłami. Produkty nie przechowują haseł użytkowników Konta (lokalne konta awaryjne zostają).
- **core_sso** (w `agency-platform-core`, wheel vendorowany jak core_audit): przycisk „Zaloguj kontem sudomie”, callback,
  wiązanie konta po (issuer, sub), rola z claimu, łączenie z istniejącym kontem lokalnym, LoginEvent. Wyjęte z Kalendarza
  (`przyjecia/oidc.py`, `uslugi.konto_z_oidc`, `TozsamoscZewnetrzna`), które już działa i ma testy.
- **Dostawca OIDC** — kod przenoszony z gałęzi `sso-oidc` Grafiku (`core/oidc.py`, `klient_oidc`, ustawienia DOT, testy
  `core/test_oidc.py`): RS256, PKCE wymagane, bez ekranu zgody dla własnych produktów, discovery, userinfo, wylogowanie RP.

## Model danych (Konto)
| Model | Pola | Uwagi |
|---|---|---|
| `Firma` | id (uuid), nazwa, utworzono | restauracja, hotel, biuro |
| `Produkt` | kod (`grafik`, `kalendarz`…), nazwa, adres, role (lista z pliku danych), klient OIDC | rejestr produktów w `produkty.json` (data-driven) |
| `User` | django.contrib.auth (login = e-mail, małe litery) | hasło tylko tu |
| `Czlonkostwo` | firma, user, `wlasciciel` (bool), aktywne | właściciel zarządza dostępami |
| `Dostep` | czlonkostwo, produkt, rola | rola z listy ról produktu; brak wiersza = brak dostępu |
| `Zaproszenie` | firma, e-mail, dostępy (JSON), hash tokenu, ważne do | link jednorazowy, jak w Grafiku |
| `TokenAplikacji` | (DOT Application, client credentials) | API produkt↔produkt |
Wszystko z `HistoricalRecords()`, logowania w `LoginEvent` (core_audit), IP z X-Forwarded-For.

## Kontrakt claimów v2 (id_token + userinfo)
```json
{
  "sub": "<stałe id konta>",
  "preferred_username": "marcin@...", "name": "Marcin", "email": "marcin@...", "email_verified": true,
  "firmy": [
    {"id": "<uuid firmy>", "nazwa": "Sami Swoi", "wlasciciel": true,
     "produkty": {"grafik": "dyrektor", "kalendarz": "kierownik"}}
  ]
}
```
Klient czyta **tylko swój klucz** w `produkty` (np. `kalendarz`). Brak klucza = brak dostępu.
(Zmiana względem wersji z Grafiku: `rola` → `produkty{}`; w Kalendarzu jedna funkcja do poprawy.)

## Powiązanie firm Konta z produktami
Każdy produkt ma własną „firmę” (Grafik: Workplace, InnDesk: hotel, Kalendarz: jedna instalacja = jeden lokal).
Produkt trzyma `konto_firma_id` przy swojej firmie (wielofirmowe: pole w modelu; jednofirmowe jak Kalendarz: zmienna
`KALENDARZ_FIRMA` w .env). Przy pierwszym podpięciu firmy: kierownik produktu wybiera „połącz z firmą w Koncie”.

## Migracja istniejących kont (bez przejmowania cudzych kont)
1. Użytkownik loguje się kontem sudomie → produkt nie zna jeszcze (issuer, sub).
2. Ekran: „Masz już konto w <produkcie>? Podaj jego login i hasło raz, połączymy je.” → po poprawnym haśle lokalne
   konto dostaje powiązanie; dane i historia zostają przy nim. Albo „Nie mam konta” → nowe konto lokalne.
3. Nigdy automatycznie po loginie/e-mailu (test negatywny — już jest w Kalendarzu).
4. Po migracji firmy produkt może wyłączyć logowanie hasłem dla jej osób (flaga per produkt).

## Ekrany Konta (Django + Inertia + React/shadcn, standard od 2026-11-16)
- **Logowanie** (marka sudomie; nazwa produktu, z którego przyszedł: „Zaloguj się do Kalendarza przyjęć”), reset hasła, zaproszenie.
- **Moje konto**: imię, e-mail, hasło, moje firmy i produkty (kafelki „przejdź do Grafiku” → SSO bez hasła).
- **Firma → Zespół** (właściciel): tabela osoby × produkty z rolą w każdej komórce; dodaj (zaproszenie e-mailem), zmień, wyłącz.
  Pełny CRUD od pierwszej wersji (CLAUDE.md). Audyt przed oddaniem: tabela rzecz × lista/dodaj/zmień/usuń.
- **Firma → Produkty**: które produkty firma ma, link do każdego.
- Serwis (jazzmin, `/serwis/`): produkty, klienci OIDC, firmy — tylko dla nas.

## Bezpieczeństwo
- PKCE wymagane, RS256, klucz w pliku na serwerze (jak `deploy/oidc-klucz.sh` z Grafiku), redirect_uri dokładne.
- Throttling logowania i resetu, LoginEvent `failed` (brute-force), hasła min. 12 znaków.
- Ciasteczka: własne nazwy, Secure, `SameSite=Lax`; za tunelem `SECURE_PROXY_SSL_HEADER` + `SECURE_SSL_REDIRECT` razem.
- Później (flaga): TOTP (2FA) dla właścicieli, logowanie Google.

## Poczta
Zaproszenia i resety z `Konto sudomie <no-reply@sudomie.pl>` przez `mail.sudomie.pl:465` — wspólny nadawca całej rodziny
(decyzja 2026-11-20, CLAUDE.md).

## Etapy
1. **Konto MVP**: modele, dostawca OIDC (kod z Grafiku), logowanie/reset/zaproszenie, Moje konto, Firma → Zespół, testy praw.
2. **Wdrożenie** konto.sudomie.pl (nowy LXC — Konrad, wzór `Kalendarz/deploy/PROXMOX.md`; tunel z terminala; SMTP).
3. **core_sso** w agency-platform-core + **Kalendarz** jako pierwszy klient (już prawie gotowy) → Marcin loguje się kontem sudomie.
4. **Grafik** jako klient (łączenie kont, `konto_firma_id` przy Workplace; jego rejestracja firm przechodzi do Konta).
5. **Grupy, FoodCost, InnDesk, HotelAgenda** — po kolei, każdy jako klient.
6. **API między produktami**: tokeny aplikacji z Konta; Kalendarz → Grafik (przyjęcia), Grafik → Kalendarz (zmiany).

## Otwarte pytania
- Rejestracja nowych firm: w Koncie (jedno miejsce dla wszystkich produktów) — Grafik ma dziś własną; przenosimy w etapie 4.
- FoodCost jest na Django 5.2 z własnym modelem `accounts.User` — core_sso musi działać z `get_user_model()` (sprawdzić przy etapie 5).
- Czy właściciel firmy ma widzieć logowania swoich ludzi (z LoginEvent)? Domyślnie nie w MVP.
