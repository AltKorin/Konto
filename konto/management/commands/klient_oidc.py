"""Rejestruje produkt jako klienta OIDC Konta. Sekret wypisuje RAZ — od razu do .env klienta, nie do czatu.

  python manage.py klient_oidc kalendarz https://kalendarz.sudomie.pl/oidc/callback/ > klient-kalendarz.env
Jeden produkt = jeden klient; drugi raz nic nie tworzy (sekret jest zahaszowany, odczytać się go nie da).
"""
from django.core.management.base import BaseCommand, CommandError
from oauth2_provider.generators import generate_client_secret
from oauth2_provider.models import get_application_model

from konto.models import Produkt


class Command(BaseCommand):
    help = "Zarejestruj produkt jako klienta OIDC (confidential, authorization code + PKCE, bez ekranu zgody)."

    def add_arguments(self, parser):
        parser.add_argument("kod_produktu")
        parser.add_argument("redirect_uri", nargs="+")

    def handle(self, kod_produktu, redirect_uri, **opts):
        produkt = Produkt.objects.filter(kod=kod_produktu).first()
        if not produkt:
            raise CommandError(f"Nie ma produktu „{kod_produktu}” (manage.py wczytaj_produkty).")
        if produkt.klient_id:
            self.stderr.write(f"{produkt.nazwa} ma już klienta — nic nie zmieniono.")
            return
        App = get_application_model()
        sekret = generate_client_secret()
        app = App.objects.create(
            name=produkt.nazwa, client_type=App.CLIENT_CONFIDENTIAL,
            authorization_grant_type=App.GRANT_AUTHORIZATION_CODE, redirect_uris=" ".join(redirect_uri),
            post_logout_redirect_uris=" ".join(u.rsplit("/oidc/", 1)[0] + "/" for u in redirect_uri),
            client_secret=sekret, algorithm=App.RS256_ALGORITHM,
            skip_authorization=True,  # własne produkty: bez ekranu zgody (i bez formularza blokowanego przez CSP)
        )
        produkt.klient = app
        produkt.save(update_fields=["klient"])
        self.stdout.write(f"OIDC_ISSUER=<adres Konta>/o\nOIDC_CLIENT_ID={app.client_id}\nOIDC_CLIENT_SECRET={sekret}\n")
