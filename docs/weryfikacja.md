# Weryfikacja Konta sudomie — 2026-11-20 (#762–#764, lokalnie)

## Audyt: rzecz × lista / dodaj / zmień / usuń w panelu klienta
| Rzecz | Lista | Dodaj | Zmień | Usuń |
|---|---|---|---|---|
| Osoba w zespole (właściciel firmy) | ✅ Zespół: tabela osoby × produkty | ✅ zaproszenie e-mailem (no-reply@sudomie.pl) | ✅ dostępy do każdego produktu, rola właściciela | ✅ = wyłącz (z potwierdzeniem; historia zostaje), włącz z powrotem; ostatniego właściciela nie da się wyłączyć ani odebrać mu roli — komunikat |
| Zaproszenie | ✅ „Czekają na przyjęcie” (z datą ważności / „wygasło”) | ✅ | ✅ ponowne zaproszenie tego adresu zastępuje stare dostępy; „Wyślij ponownie” = nowy link i termin | ✅ anuluj (z potwierdzeniem); przyjętego nie da się anulować — komunikat |
| Nazwa firmy | ✅ nagłówek Zespołu | — (firmę zakładamy przy wdrożeniu klienta) | ✅ | — |
| Moje dane | ✅ Moje konto | — | ✅ imię, e-mail/login (z hasłem), hasło | ❌ usunięcie własnego konta |

**Dziury (= funkcje niegotowe, zadania w OpenProject):**
- Zakładanie nowej firmy przez klienta (rejestracja) — dziś firmę tworzymy w `/serwis/` przy wdrożeniu; samodzielna rejestracja
  przechodzi z Grafiku do Konta w #767.
- Usunięcie własnego konta (RODO — prawo do usunięcia) — nowe zadanie.
- Usunięcie firmy — świadomie tylko przez nas (koniec umowy, eksport danych z produktów), nie przez klienta.

## Bramki
- `pytest tests/` — 58 testów: prawa usług (claim = dostępy, Hypothesis; minimalizacja claimu per produkt; role z listy; zaproszenie
  jednorazowe / zastępowane / anulowane; ostatni właściciel; atomowa zmiana dostępów; wyłączona osoba znika z claimów),
  OIDC (discovery, PKCE, zły redirect_uri, claim v2), widoki (otwarte przekierowanie, enumeracja kont przy resecie, limity prób,
  jednorazowe linki, przejęcie konta przez zaproszenie, 404 dla obcych i pracowników, zmiana hasła/e-maila).
- E2E lokalnie (Playwright): logowanie → start, reset, zaproszenie → konto; Zespół: zaproszenie, edycja dostępów, wyłącz/włącz,
  anulowanie zaproszenia, ochrona ostatniego właściciela; Kalendarz loguje przez Konto (kierownik widzi Zespół, obsługa nie).
- Poczta: logowanie SMTP z serwera Konta do mail.sudomie.pl:465 jako no-reply@sudomie.pl — OK.
- Audyt: simple-history na wszystkich modelach, LoginEvent (core_audit), IP z X-Forwarded-For.
