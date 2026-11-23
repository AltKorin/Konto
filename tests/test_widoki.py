"""Ekrany logowania, resetu i zaproszenia (#763)."""
import json
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache

from core_audit.models import LoginEvent
from konto import uslugi
from konto.views import bezpieczny_next

User = get_user_model()
HASLO = "dlugie-haslo-do-testow-1"
J = {"content_type": "application/json"}
I = {"HTTP_X_INERTIA": "true"}


@pytest.fixture(autouse=True)
def czysto(db, settings):
    cache.clear()
    uslugi.wczytaj_produkty()


@pytest.fixture
def marcin(db):
    return User.objects.create_user("marcin@x.pl", "marcin@x.pl", HASLO, first_name="Marcin")


def post(client, url, dane, **kw):
    return client.post(url, json.dumps(dane), **J, **kw)


@pytest.mark.parametrize("zly", ["//zla.pl/", "https://zla.pl/", "\\\\zla.pl", "", None, "javascript:alert(1)", "/\\zla.pl"])
def test_next_bez_otwartego_przekierowania(zly):
    assert bezpieczny_next(zly) == "/"


def test_logowanie_ok_i_wraca_pod_next_oraz_loguje_zdarzenia(client, marcin):
    assert post(client, "/logowanie/?next=/o/authorize/%3Fx%3D1", {"email": " Marcin@X.pl ", "haslo": "zle"}).status_code == 200
    r = post(client, "/logowanie/?next=/o/authorize/%3Fx%3D1", {"email": " Marcin@X.pl ", "haslo": HASLO})
    assert r.status_code == 302 and r["Location"] == "/o/authorize/?x=1"
    assert set(LoginEvent.objects.values_list("event_type", flat=True)) == {"failed", "login"}


def test_logowanie_na_obcy_next_wraca_na_start(client, marcin):
    r = post(client, "/logowanie/?next=//zla.pl/", {"email": "marcin@x.pl", "haslo": HASLO})
    assert r["Location"] == "/"


def test_limit_prob_logowania(client, marcin, settings):
    settings.LIMIT_LOGOWAN_NA_MINUTE = 3
    for _ in range(3):
        post(client, "/logowanie/", {"email": "marcin@x.pl", "haslo": "zle"})
    r = post(client, "/logowanie/", {"email": "marcin@x.pl", "haslo": HASLO}, **I)
    assert "Za dużo prób" in r.json()["props"]["bledy"]["haslo"]


def test_reset_nie_zdradza_czy_konto_istnieje_i_link_dziala_raz(client, marcin):
    a = post(client, "/reset-hasla/", {"email": "nikt@x.pl"}, **I).json()["props"]
    b = post(client, "/reset-hasla/", {"email": "MARCIN@x.pl"}, **I).json()["props"]
    assert a == b == {**a, "wyslano": True, "blad": None}
    assert len(mail.outbox) == 1 and mail.outbox[0].from_email == "Konto sudomie <no-reply@sudomie.pl>"
    link = re.search(r"https?://\S+/nowe-haslo/\S+/", mail.outbox[0].body).group(0)
    sciezka = link.split("testserver", 1)[1]
    assert post(client, sciezka, {"haslo": "nowe-dlugie-haslo-2", "powtorz": "inne"}, **I).json()["props"]["bledy"]["powtorz"]
    assert post(client, sciezka, {"haslo": "krotkie", "powtorz": "krotkie"}, **I).json()["props"]["bledy"]["haslo"]
    assert post(client, sciezka, {"haslo": "nowe-dlugie-haslo-2", "powtorz": "nowe-dlugie-haslo-2"}).status_code == 302
    marcin.refresh_from_db()
    assert marcin.check_password("nowe-dlugie-haslo-2")
    client.logout()
    assert client.get(sciezka, **I).json()["props"]["wazny"] is False  # drugi raz nie zadziała


def test_reset_zly_email_i_limit(client, settings):
    assert post(client, "/reset-hasla/", {"email": "bez-malpy"}, **I).json()["props"]["blad"]
    settings.LIMIT_RESETOW_NA_GODZINE = 2
    for _ in range(2):
        post(client, "/reset-hasla/", {"email": "a@x.pl"})
    assert "Za dużo" in post(client, "/reset-hasla/", {"email": "a@x.pl"}, **I).json()["props"]["blad"]


def test_nowe_haslo_smieciowy_link(client):
    for url in ["/nowe-haslo/xxx/yyy/", "/nowe-haslo/MQ/zly-token/", "/nowe-haslo/%00/x/"]:
        assert client.get(url, **I).json()["props"]["wazny"] is False


def test_zaproszenie_nowej_osoby_zaklada_konto_i_loguje(client, marcin):
    f = uslugi.zaloz_firme("Sami Swoi", marcin)
    z, token = uslugi.zapros(f, "ania@x.pl", {"kalendarz": "obsluga"}, imie="Ania")
    props = client.get(f"/zaproszenie/{token}/", **I).json()["props"]
    assert props["firma"] == "Sami Swoi" and props["produkty"] == [{"nazwa": "Kalendarz przyjęć", "rola": "obsluga"}]
    assert post(client, f"/zaproszenie/{token}/", {"haslo": HASLO, "powtorz": "inne"}, **I).json()["props"]["bledy"]["haslo"]
    r = post(client, f"/zaproszenie/{token}/", {"haslo": HASLO, "powtorz": HASLO})
    assert r.status_code == 302 and client.get("/", **I).json()["props"]["firmy"][0]["produkty"][0]["kod"] == "kalendarz"
    assert client.get(f"/zaproszenie/{token}/", **I).json()["props"]["blad"]  # drugi raz nieważne


def test_zaproszenie_dla_istniejacego_konta_wymaga_zalogowania(client, marcin):
    szef = User.objects.create_user("szef@x.pl", "szef@x.pl", HASLO)
    f = uslugi.zaloz_firme("A", szef)
    _, token = uslugi.zapros(f, "marcin@x.pl", {"grafik": "kierownik"})
    props = client.get(f"/zaproszenie/{token}/", **I).json()["props"]
    assert props["konto_istnieje"] and not props["zalogowany_jako"]
    assert post(client, f"/zaproszenie/{token}/", {"haslo": "przejmuje-cudze-konto", "powtorz": "przejmuje-cudze-konto"}, **I).json()["props"]["bledy"]["haslo"]
    marcin.refresh_from_db()
    assert marcin.check_password(HASLO)
    client.force_login(marcin)
    assert post(client, f"/zaproszenie/{token}/", {}).status_code == 302
    assert uslugi.firmy_do_claimu(marcin)[0]["produkty"] == {"grafik": "kierownik"}


def test_start_wymaga_logowania(client):
    assert client.get("/")["Location"].startswith("/logowanie/")


def test_ekran_logowania_pokazuje_produkt_z_oidc(client, marcin):
    from django.core.management import call_command
    import io
    out = io.StringIO()
    call_command("klient_oidc", "kalendarz", "https://k.test/oidc/callback/", stdout=out)
    cid = re.search(r"OIDC_CLIENT_ID=(\S+)", out.getvalue()).group(1)
    r = client.get(f"/logowanie/?next=/o/authorize/%3Fclient_id%3D{cid}%26response_type%3Dcode", **I)
    assert r.json()["props"]["produkt"] == "Kalendarz przyjęć"


def test_logowanie_z_inertii_konczy_sie_pelnym_przejsciem(client, marcin):
    r = post(client, "/logowanie/?next=/o/authorize/%3Fx%3D1", {"email": "marcin@x.pl", "haslo": HASLO}, **I)
    assert r.status_code == 409 and r["X-Inertia-Location"] == "/o/authorize/?x=1"
