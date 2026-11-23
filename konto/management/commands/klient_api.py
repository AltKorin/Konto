"""Rejestruje produkt jako klienta API (client credentials, scope `api`) — token serwer–serwer, bez użytkownika.

  python manage.py klient_api grafik > klient-api-grafik.env
Pierwszy konsument: Grafik czyta przyjęcia z Kalendarza (OpenProject #758). Serwer API sprawdza token introspekcją
(`/o/introspect/`, Basic auth własnym klientem OIDC) i wpuszcza tylko client_id ze swojej listy (`API_KLIENCI`).
Osobna aplikacja DOT, bo jedna aplikacja = jeden grant (klient logowania ma authorization code).
Drugi raz nic nie tworzy — sekret jest zahaszowany.
"""
from django.core.management.base import BaseCommand, CommandError
from oauth2_provider.generators import generate_client_secret
from oauth2_provider.models import get_application_model

from konto.models import Produkt


class Command(BaseCommand):
    help = "Zarejestruj produkt jako klienta API (client credentials) — token aplikacji do API innych produktów."

    def add_arguments(self, parser):
        parser.add_argument("kod_produktu")

    def handle(self, kod_produktu, **opts):
        produkt = Produkt.objects.filter(kod=kod_produktu).first()
        if not produkt:
            raise CommandError(f"Nie ma produktu „{kod_produktu}” (manage.py wczytaj_produkty).")
        App = get_application_model()
        nazwa = f"{produkt.nazwa} — API"
        if App.objects.filter(name=nazwa, authorization_grant_type=App.GRANT_CLIENT_CREDENTIALS).exists():
            self.stderr.write(f"{nazwa} już jest — nic nie zmieniono.")
            return
        sekret = generate_client_secret()
        app = App.objects.create(name=nazwa, client_type=App.CLIENT_CONFIDENTIAL,
                                 authorization_grant_type=App.GRANT_CLIENT_CREDENTIALS, client_secret=sekret)
        self.stdout.write(f"KONTO_API_CLIENT_ID={app.client_id}\nKONTO_API_CLIENT_SECRET={sekret}\n")
