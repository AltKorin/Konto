"""Zespół firmy i Moje konto (#764) — prawa z uslugi.py."""
import json
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache

from konto import uslugi
from konto.models import Czlonkostwo, Dostep, Zaproszenie

User = get_user_model()
HASLO = "dlugie-haslo-do-testow-1"
J = {"content_type": "application/json"}
I = {"HTTP_X_INERTIA": "true"}


@pytest.fixture(autouse=True)
def czysto(db):
    cache.clear()
    uslugi.wczytaj_produkty()


@pytest.fixture
def firma(db):
    szef = User.objects.create_user("szef@x.pl", "szef@x.pl", HASLO, first_name="Szef")
    f = uslugi.zaloz_firme("Sami Swoi", szef)
    ania = User.objects.create_user("ania@x.pl", "ania@x.pl", HASLO, first_name="Ania")
    c = Czlonkostwo.objects.create(firma=f, user=ania)
    uslugi.ustaw_dostep(c, "kalendarz", "obsluga")
    return f, szef, ania, c


def post(client, url, dane=None, **kw):
    return client.post(url, json.dumps(dane or {}), **J, **kw)


def wl(f, u):
    return Czlonkostwo.objects.get(firma=f, user=u)


def test_ostatni_wlasciciel_nie_traci_roli_ani_dostepu(firma):
    f, szef, ania, _ = firma
    with pytest.raises(uslugi.BladKonta):
        uslugi.ustaw_wlasciciela(wl(f, szef), False)
    with pytest.raises(uslugi.BladKonta):
        uslugi.ustaw_aktywne(wl(f, szef), False)
    assert wl(f, szef).wlasciciel and wl(f, szef).aktywne
    uslugi.ustaw_wlasciciela(wl(f, ania), True)
    uslugi.ustaw_wlasciciela(wl(f, szef), False)  # teraz można — Ania jest właścicielką
    assert not wl(f, szef).wlasciciel


def test_zmiana_dostepow_atomowa(firma):
    f, _, _, c = firma
    with pytest.raises(uslugi.BladKonta):
        uslugi.zmien_dostepy(c, {"grafik": "pracownik", "kalendarz": "dyrektor"})
    with pytest.raises(uslugi.BladKonta):
        uslugi.zmien_dostepy(c, {"grafik": "pracownik", "nieznany": ""})
    assert dict(Dostep.objects.filter(czlonkostwo=c).values_list("produkt__kod", "rola")) == {"kalendarz": "obsluga"}
    uslugi.zmien_dostepy(c, {"grafik": "pracownik", "kalendarz": ""})
    assert dict(Dostep.objects.filter(czlonkostwo=c).values_list("produkt__kod", "rola")) == {"grafik": "pracownik"}


def test_wylaczona_osoba_znika_z_claimow_i_wraca(firma):
    f, _, ania, c = firma
    uslugi.ustaw_aktywne(c, False)
    assert uslugi.firmy_do_claimu(ania) == []
    uslugi.ustaw_aktywne(c, True)
    assert uslugi.firmy_do_claimu(ania)[0]["produkty"] == {"kalendarz": "obsluga"}


@pytest.mark.parametrize("nazwa", ["", "   ", None, "x" * 201])
def test_zla_nazwa_firmy(firma, nazwa):
    with pytest.raises(uslugi.BladKonta):
        uslugi.zmien_nazwe_firmy(firma[0], nazwa)


def test_anulowanie_i_odnowienie_zaproszenia(firma):
    f = firma[0]
    z, t1 = uslugi.zapros(f, "ola@x.pl", {"grafik": "pracownik"})
    t2 = uslugi.odnow_zaproszenie(z)
    with pytest.raises(uslugi.BladKonta):
        uslugi.zaproszenie_po_tokenie(t1)  # stary link nie działa
    assert uslugi.zaproszenie_po_tokenie(t2)
    uslugi.anuluj_zaproszenie(z)
    with pytest.raises(uslugi.BladKonta):
        uslugi.zaproszenie_po_tokenie(t2)


def test_przyjetego_zaproszenia_nie_da_sie_anulowac(firma):
    z, t = uslugi.zapros(firma[0], "ola@x.pl", {})
    uslugi.przyjmij_zaproszenie(t, HASLO)
    z.refresh_from_db()
    with pytest.raises(uslugi.BladKonta):
        uslugi.anuluj_zaproszenie(z)


# ---------- widoki: tylko właściciel, 404 dla reszty ----------

def test_obcy_i_pracownik_dostaja_404(client, firma):
    f, _, ania, c = firma
    obcy = User.objects.create_user("obcy@x.pl", "obcy@x.pl", HASLO)
    for u in (obcy, ania):
        client.force_login(u)
        assert client.get(f"/firma/{f.id}/zespol/").status_code == 404
        assert post(client, f"/firma/{f.id}/osoba/{c.pk}/", {"dostepy": {"grafik": "dyrektor"}}).status_code == 404
        assert post(client, f"/firma/{f.id}/zapros/", {"email": "x@x.pl"}).status_code == 404
    client.logout()
    assert client.get(f"/firma/{f.id}/zespol/").status_code == 302


def test_wlasciciel_nie_zmieni_osoby_z_innej_firmy(client, firma):
    f, szef, _, _ = firma
    inny = User.objects.create_user("inny@x.pl", "inny@x.pl", HASLO)
    f2 = uslugi.zaloz_firme("Inna", inny)
    client.force_login(szef)
    assert post(client, f"/firma/{f.id}/osoba/{wl(f2, inny).pk}/", {"aktywne": False}).status_code == 404
    assert wl(f2, inny).aktywne


def test_zaproszenie_z_ekranu_wysyla_mail_i_link_dziala(client, firma):
    f, szef, _, _ = firma
    client.force_login(szef)
    post(client, f"/firma/{f.id}/zapros/", {"email": "Ola@X.pl", "imie": "Ola", "dostepy": {"grafik": "pracownik", "kalendarz": ""}})
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["ola@x.pl"] and "Sami Swoi" in mail.outbox[0].subject
    token = re.search(r"/zaproszenie/([^/\s]+)/", mail.outbox[0].body).group(1)
    assert uslugi.zaproszenie_po_tokenie(token).dostepy == {"grafik": "pracownik"}
    props = client.get(f"/firma/{f.id}/zespol/", **I).json()["props"]
    assert props["zaproszenia"][0]["email"] == "ola@x.pl" and len(props["osoby"]) == 2


def test_blad_z_ekranu_nie_zmienia_nic_i_pokazuje_komunikat(client, firma):
    f, szef, _, c = firma
    client.force_login(szef)
    r = post(client, f"/firma/{f.id}/osoba/{wl(f, szef).pk}/", {"wlasciciel": False}, follow=True, **I)
    assert any("co najmniej jednego właściciela" in k["tekst"] for k in r.json()["props"]["komunikaty"])
    post(client, f"/firma/{f.id}/osoba/{c.pk}/", {"dostepy": {"grafik": "pracownik", "kalendarz": "zla"}})
    assert dict(Dostep.objects.filter(czlonkostwo=c).values_list("produkt__kod", "rola")) == {"kalendarz": "obsluga"}


# ---------- moje konto ----------

def test_zmiana_hasla_wymaga_obecnego_i_zostawia_zalogowanym(client, firma):
    _, szef, _, _ = firma
    client.force_login(szef)
    post(client, "/moje-konto/", {"co": "haslo", "obecne": "zle", "nowe": "nowe-dlugie-haslo-9", "powtorz": "nowe-dlugie-haslo-9"})
    szef.refresh_from_db()
    assert szef.check_password(HASLO)
    post(client, "/moje-konto/", {"co": "haslo", "obecne": HASLO, "nowe": "nowe-dlugie-haslo-9", "powtorz": "nowe-dlugie-haslo-9"})
    szef.refresh_from_db()
    assert szef.check_password("nowe-dlugie-haslo-9") and client.get("/moje-konto/").status_code == 200


def test_zmiana_emaila_wymaga_hasla_i_wolnego_adresu(firma):
    _, szef, ania, _ = firma
    with pytest.raises(uslugi.BladKonta):
        uslugi.zmien_moje_dane(szef, "Szef", "nowy@x.pl", "zle-haslo")
    with pytest.raises(uslugi.BladKonta):
        uslugi.zmien_moje_dane(szef, "Szef", "ANIA@x.pl", HASLO)
    with pytest.raises(uslugi.BladKonta):
        uslugi.zmien_moje_dane(szef, "Szef", "bez-malpy", HASLO)
    uslugi.zmien_moje_dane(szef, "Szef Główny", "Nowy@X.pl", HASLO)
    szef.refresh_from_db()
    assert szef.username == szef.email == "nowy@x.pl" and szef.first_name == "Szef Główny"


def test_ponowne_zaproszenie_zastepuje_stare_a_czlonek_nie_dostaje_zaproszenia(firma):
    f = firma[0]
    _, t1 = uslugi.zapros(f, "ola@x.pl", {"grafik": "pracownik"})
    z2, t2 = uslugi.zapros(f, "OLA@x.pl", {"kalendarz": "obsluga"})
    assert Zaproszenie.objects.filter(firma=f, email="ola@x.pl").count() == 1
    with pytest.raises(uslugi.BladKonta):
        uslugi.zaproszenie_po_tokenie(t1)
    assert uslugi.zaproszenie_po_tokenie(t2).dostepy == {"kalendarz": "obsluga"}
    with pytest.raises(uslugi.BladKonta, match="już jest w zespole"):
        uslugi.zapros(f, "ania@x.pl", {"grafik": "pracownik"})
