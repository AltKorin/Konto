"""Rejestracja firmy (konto/uslugi.zarejestruj_firme + widok /rejestracja/) — prawa w docstringu uslugi."""
import json
import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.utils import timezone

from konto import uslugi
from konto.models import Czlonkostwo, Firma, Zaproszenie

User = get_user_model()
HASLO = "dlugie-haslo-do-testow-1"
J = {"content_type": "application/json"}
I = {"HTTP_X_INERTIA": "true"}
DANE = {"nazwa": "Gospoda pod Lipą", "imie": "Ala", "email": "Ala@Gospoda.pl", "produkt": "kalendarz"}


@pytest.fixture(autouse=True)
def czysto(db, settings):
    cache.clear()
    uslugi.wczytaj_produkty()
    settings.REJESTRACJA_WLACZONA = True
    settings.REJESTRACJA_NA_GODZINE = 50


def rejestruj(client, **zmiany):
    return client.post("/rejestracja/", json.dumps({**DANE, **zmiany}), **J, **I)


def link():
    return re.search(r"https?://\S+/zaproszenie/(\S+)/", mail.outbox[-1].body).group(1)


def test_rejestracja_link_haslo_i_wlasciciel_z_najszersza_rola(client):
    r = rejestruj(client)
    assert r.json()["props"]["wyslano"] and len(mail.outbox) == 1 and mail.outbox[0].to == ["ala@gospoda.pl"]
    firma = Firma.objects.get()
    assert firma.rejestracja and not firma.czlonkostwa.exists()
    assert uslugi.firmy_do_claimu(User.objects.create_user("ktos")) == []  # przed kliknięciem nic nie daje
    token = link()
    r = client.post(f"/zaproszenie/{token}/", json.dumps({"haslo": HASLO, "powtorz": HASLO}), **J)
    assert r.status_code == 302
    firma.refresh_from_db()
    ala = User.objects.get(username="ala@gospoda.pl")
    c = Czlonkostwo.objects.get(firma=firma, user=ala)
    assert c.wlasciciel and firma.rejestracja is None
    assert uslugi.firmy_do_claimu(ala)[0]["produkty"] == {"kalendarz": "kierownik"}


def test_istniejace_konto_nie_jest_zdradzane_i_dolacza_po_zalogowaniu(client):
    ala = User.objects.create_user("ala@gospoda.pl", "ala@gospoda.pl", HASLO)
    r = rejestruj(client)
    assert r.json()["props"]["wyslano"]  # ta sama odpowiedź co dla nowego adresu
    client.force_login(ala)
    client.post(f"/zaproszenie/{link()}/")
    assert Czlonkostwo.objects.get(user=ala).wlasciciel


@pytest.mark.parametrize("zle", [{"nazwa": "  "}, {"email": "nie-mail"}, {"produkt": "kasyno"}, {"produkt": ""}])
def test_zle_dane_nic_nie_tworza(client, zle):
    r = rejestruj(client, **zle)
    assert r.json()["props"]["bledy"] and not Firma.objects.exists() and not mail.outbox


def test_wylaczona_flaga_404(client, settings):
    settings.REJESTRACJA_WLACZONA = False
    assert client.get("/rejestracja/").status_code == 404
    assert rejestruj(client).status_code == 404 and not Firma.objects.exists()


def test_limit_na_ip(client, settings):
    settings.REJESTRACJA_NA_GODZINE = 2
    for i in range(3):
        rejestruj(client, email=f"a{i}@x.pl")
    assert Firma.objects.count() == 2


def test_limit_oczekujacych(client, settings):
    settings.REJESTRACJA_MAX_OCZEKUJACYCH = 1
    rejestruj(client, email="a@x.pl")
    r = rejestruj(client, email="b@x.pl")
    assert "Za dużo" in r.json()["props"]["bledy"]["email"] and Firma.objects.count() == 1


def test_ponowna_rejestracja_tego_adresu_zastepuje_poprzednia(client):
    rejestruj(client)
    stary = link()
    rejestruj(client, nazwa="Gospoda pod Lipą sp.j.")
    assert list(Firma.objects.values_list("nazwa", flat=True)) == ["Gospoda pod Lipą sp.j."]
    r = client.get(f"/zaproszenie/{stary}/", **I)
    assert r.json()["props"]["blad"]


def test_porzucona_znika_a_nasze_firmy_zostaja(client):
    nasza = Firma.objects.create(nazwa="Sami Swoi")  # założona przez nas, bez członków i bez rejestracji
    rejestruj(client, email="porzucona@x.pl")
    Zaproszenie.objects.update(wazne_do=timezone.now() - timedelta(minutes=1))
    uslugi.sprzatnij_rejestracje()
    assert list(Firma.objects.all()) == [nasza]


def test_logowanie_pokazuje_link_tylko_z_flaga(client, settings):
    assert client.get("/logowanie/", **I).json()["props"]["rejestracja"] is True
    settings.REJESTRACJA_WLACZONA = False
    assert client.get("/logowanie/", **I).json()["props"]["rejestracja"] is False
