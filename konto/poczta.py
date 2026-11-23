"""Maile Konta. Nadawca całej rodziny: no-reply@sudomie.pl (CLAUDE.md). Treść tekstowa — czytelna w każdym programie."""
from django.conf import settings
from django.core.mail import send_mail

STOPKA = "\n\n—\nKonto sudomie — jeden login do Grafiku, Kalendarza przyjęć i innych aplikacji sudomie.\nTo wiadomość automatyczna, nie odpowiadaj na nią."


def wyslij_reset(email, link):
    send_mail(
        "Ustaw nowe hasło do Konta sudomie",
        f"Dzień dobry,\n\nktoś (mamy nadzieję, że Ty) poprosił o nowe hasło do Konta sudomie.\n"
        f"Ustaw je tutaj (link działa przez 3 dni i tylko raz):\n\n{link}\n\n"
        f"Jeśli to nie Ty — zignoruj tę wiadomość, hasło się nie zmieni." + STOPKA,
        settings.DEFAULT_FROM_EMAIL, [email])


def wyslij_zaproszenie(zaproszenie, link, kto_zaprasza=""):
    produkty = ", ".join(sorted(zaproszenie.dostepy)) or "—"
    od = f" ({kto_zaprasza})" if kto_zaprasza else ""
    send_mail(
        f"Zaproszenie do zespołu {zaproszenie.firma.nazwa}",
        f"Dzień dobry{(' ' + zaproszenie.imie) if zaproszenie.imie else ''},\n\n"
        f"{zaproszenie.firma.nazwa}{od} zaprasza Cię do pracy w aplikacjach sudomie: {produkty}.\n"
        f"Załóż hasło i dołącz (link ważny do {zaproszenie.wazne_do:%d.%m.%Y}, działa raz):\n\n{link}" + STOPKA,
        settings.DEFAULT_FROM_EMAIL, [zaproszenie.email])


def wyslij_rejestracje(zaproszenie, link, produkt):
    send_mail(
        f"Potwierdź założenie firmy {zaproszenie.firma.nazwa}",
        f"Dzień dobry{(' ' + zaproszenie.imie) if zaproszenie.imie else ''},\n\n"
        f"ktoś (mamy nadzieję, że Ty) zakłada firmę „{zaproszenie.firma.nazwa}” w Koncie sudomie, żeby korzystać z: {produkt}.\n"
        f"Potwierdź adres i ustaw hasło (link ważny do {zaproszenie.wazne_do:%d.%m.%Y}, działa raz):\n\n{link}\n\n"
        f"Jeśli to nie Ty — zignoruj tę wiadomość. Bez kliknięcia firma nie powstanie." + STOPKA,
        settings.DEFAULT_FROM_EMAIL, [zaproszenie.email])
