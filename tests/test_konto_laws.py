"""Prawa serwisów Konta (docstring konto/uslugi.py)."""
import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from hypothesis import given, settings as hset, strategies as st
from hypothesis.extra.django import TestCase as HTestCase

from konto import uslugi
from konto.models import Czlonkostwo, Dostep, Firma, Produkt, Zaproszenie

User = get_user_model()
HASLO = "dlugie-haslo-do-testow-1"


@pytest.fixture(autouse=True)
def produkty(db):
    uslugi.wczytaj_produkty()


def osoba(email="marcin@x.pl"):
    return User.objects.create_user(email, email, HASLO)


def test_wczytaj_produkty_idempotentne():
    assert all(not nowy for _, nowy in uslugi.wczytaj_produkty())
    assert Produkt.objects.count() == 6


def test_claim_tylko_aktywne_i_tylko_produkty_z_dostepem():
    u = osoba()
    f = uslugi.zaloz_firme("Sami Swoi", u)
    c = Czlonkostwo.objects.get(firma=f, user=u)
    uslugi.ustaw_dostep(c, "kalendarz", "kierownik")
    uslugi.ustaw_dostep(c, "grafik", "dyrektor")
    stara = uslugi.zaloz_firme("Stara", u)
    Czlonkostwo.objects.filter(firma=stara).update(aktywne=False)
    wylaczona = uslugi.zaloz_firme("Wyłączona", u)
    wylaczona.aktywna = False
    wylaczona.save()
    assert uslugi.firmy_do_claimu(u) == [{"id": str(f.id), "nazwa": "Sami Swoi", "wlasciciel": True,
                                           "produkty": {"grafik": "dyrektor", "kalendarz": "kierownik"}}]


def test_klient_produktu_widzi_tylko_swoj_klucz_i_firmy_z_dostepem():
    u = osoba()
    f1, f2 = uslugi.zaloz_firme("A", u), uslugi.zaloz_firme("B", u)
    uslugi.ustaw_dostep(Czlonkostwo.objects.get(firma=f1), "kalendarz", "obsluga")
    uslugi.ustaw_dostep(Czlonkostwo.objects.get(firma=f1), "grafik", "pracownik")
    uslugi.ustaw_dostep(Czlonkostwo.objects.get(firma=f2), "grafik", "dyrektor")
    kal = Produkt.objects.get(kod="kalendarz")
    assert uslugi.firmy_do_claimu(u, kal) == [{"id": str(f1.id), "nazwa": "A", "wlasciciel": True,
                                                "produkty": {"kalendarz": "obsluga"}}]


@pytest.mark.parametrize("kod,rola", [("kalendarz", "dyrektor"), ("kalendarz", ""), ("nieznany", "kierownik"),
                                      ("grafik", "Dyrektor"), ("grafik", " dyrektor")])
def test_zla_rola_albo_produkt_nie_zapisuje_nic(kod, rola):
    u = osoba()
    c = Czlonkostwo.objects.get(firma=uslugi.zaloz_firme("A", u))
    if rola == "":  # pusta rola = zabranie dostępu, nie błąd
        assert uslugi.ustaw_dostep(c, "kalendarz", "") is None
        return
    with pytest.raises(uslugi.BladKonta):
        uslugi.ustaw_dostep(c, kod, rola)
    assert Dostep.objects.count() == 0


@pytest.mark.parametrize("email", ["", "   ", "bez-malpy", "a@", None, "x" * 300 + "@x.pl"])
def test_zly_email_w_zaproszeniu(email):
    f = uslugi.zaloz_firme("A", osoba())
    with pytest.raises(uslugi.BladKonta):
        uslugi.zapros(f, email, {"kalendarz": "obsluga"})
    assert Zaproszenie.objects.count() == 0


def test_zaproszenie_jednorazowe_i_email_malymi_literami():
    f = uslugi.zaloz_firme("A", osoba())
    z, token = uslugi.zapros(f, "  Ania@Kuchnia.PL ", {"kalendarz": "obsluga"}, imie="Ania")
    assert z.email == "ania@kuchnia.pl" and token not in z.token_hash
    u, c = uslugi.przyjmij_zaproszenie(token, HASLO)
    assert u.username == "ania@kuchnia.pl" and u.check_password(HASLO)
    assert uslugi.firmy_do_claimu(u)[0]["produkty"] == {"kalendarz": "obsluga"}
    with pytest.raises(uslugi.BladKonta):
        uslugi.przyjmij_zaproszenie(token, HASLO)
    assert User.objects.filter(username="ania@kuchnia.pl").count() == 1


def test_zaproszenie_wygasle_zly_token_i_slabe_haslo():
    f = uslugi.zaloz_firme("A", osoba())
    z, token = uslugi.zapros(f, "ola@x.pl", {})
    for zly in ["", "abc", None, token + "x"]:
        with pytest.raises(uslugi.BladKonta):
            uslugi.przyjmij_zaproszenie(zly, HASLO)
    with pytest.raises(uslugi.BladKonta):
        uslugi.przyjmij_zaproszenie(token, "krotkie")
    assert not User.objects.filter(username="ola@x.pl").exists() and Zaproszenie.objects.get().uzyte is None
    Zaproszenie.objects.update(wazne_do=timezone.now() - timedelta(seconds=1))
    with pytest.raises(uslugi.BladKonta):
        uslugi.przyjmij_zaproszenie(token, HASLO)


def test_zaproszenie_z_zla_rola_nie_powstaje():
    f = uslugi.zaloz_firme("A", osoba())
    with pytest.raises(uslugi.BladKonta):
        uslugi.zapros(f, "ola@x.pl", {"kalendarz": "dyrektor"})
    with pytest.raises(uslugi.BladKonta):
        uslugi.zapros(f, "ola@x.pl", ["kalendarz"])


def test_istniejaca_osoba_dolacza_swoim_kontem_bez_drugiego_czlonkostwa():
    szef, ania = osoba("szef@x.pl"), osoba("ania@x.pl")
    f = uslugi.zaloz_firme("A", szef)
    _, t1 = uslugi.zapros(f, "ania@x.pl", {"grafik": "pracownik"})
    with pytest.raises(uslugi.BladKonta, match="Masz już konto"):
        uslugi.przyjmij_zaproszenie(t1, HASLO)  # nie nadpisujemy hasła istniejącego konta
    uslugi.przyjmij_zaproszenie(t1, user=ania)
    with pytest.raises(uslugi.BladKonta, match="już jest w zespole"):  # członkowi zmienia się dostępy, nie zaprasza drugi raz
        uslugi.zapros(f, "ania@x.pl", {"kalendarz": "obsluga"})
    uslugi.ustaw_dostep(Czlonkostwo.objects.get(firma=f, user=ania), "kalendarz", "obsluga")
    assert Czlonkostwo.objects.filter(firma=f, user=ania).count() == 1
    assert uslugi.firmy_do_claimu(ania)[0]["produkty"] == {"grafik": "pracownik", "kalendarz": "obsluga"}


class PrawaClaimu(HTestCase):
    @hset(max_examples=60, deadline=None)
    @given(st.dictionaries(st.sampled_from(["grafik", "kalendarz", "grupy", "foodcost", "inndesk", "hotelagenda"]),
                           st.booleans()))
    def test_claim_zgodny_z_dostepami(self, wybor):
        uslugi.wczytaj_produkty()
        u = User.objects.create_user(f"h{User.objects.count()}@x.pl", None, HASLO)
        c = Czlonkostwo.objects.get(firma=uslugi.zaloz_firme("H", u))
        oczekiwane = {}
        for kod, dac in wybor.items():
            rola = Produkt.objects.get(kod=kod).role[0]
            uslugi.ustaw_dostep(c, kod, rola if dac else "")
            if dac:
                oczekiwane[kod] = rola
        assert uslugi.firmy_do_claimu(u)[0]["produkty"] == oczekiwane
        for p in Produkt.objects.all():
            claim = uslugi.firmy_do_claimu(u, p)
            assert (claim[0]["produkty"] == {p.kod: oczekiwane[p.kod]}) if p.kod in oczekiwane else claim == []
