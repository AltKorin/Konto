"""Konto jako dostawca OIDC (przeniesione z gałęzi sso-oidc Grafiku + kontrakt v2)."""
import base64
import hashlib
import io
import json
import secrets
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from konto import uslugi
from konto.models import Czlonkostwo, Produkt

REDIRECT = "https://kalendarz.test/oidc/callback/"
User = get_user_model()


def jwt(token):
    p = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


@pytest.fixture
def klient(db):
    uslugi.wczytaj_produkty()
    out = io.StringIO()
    call_command("klient_oidc", "kalendarz", REDIRECT, stdout=out)
    env = dict(l.split("=", 1) for l in out.getvalue().split() if l.startswith("OIDC_CLIENT"))
    return env["OIDC_CLIENT_ID"], env["OIDC_CLIENT_SECRET"]


@pytest.fixture
def marcin(db):
    u = User.objects.create_user("marcin@x.pl", "marcin@x.pl", "dlugie-haslo-do-testow-1", first_name="Marcin")
    f = uslugi.zaloz_firme("Sami Swoi", u)
    c = Czlonkostwo.objects.get(firma=f, user=u)
    uslugi.ustaw_dostep(c, "kalendarz", "kierownik")
    uslugi.ustaw_dostep(c, "grafik", "dyrektor")
    return u, f


def authorize(client, client_id, redirect=REDIRECT, pkce=True):
    verifier = secrets.token_urlsafe(48)
    q = {"client_id": client_id, "response_type": "code", "redirect_uri": redirect,
         "scope": "openid profile email firmy", "state": "s1", "nonce": "n1"}
    if pkce:
        q |= {"code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode(),
              "code_challenge_method": "S256"}
    return client.get("/o/authorize/", q), verifier


def test_discovery(client, db):
    d = client.get("/o/.well-known/openid-configuration/").json()
    assert d["authorization_endpoint"].endswith("/o/authorize/") and "RS256" in d["id_token_signing_alg_values_supported"]


def test_bez_sesji_odsyla_do_logowania(client, klient):
    r, _ = authorize(client, klient[0])
    assert r.status_code == 302 and r["Location"].startswith("/logowanie/?next=/o/authorize/")


def test_pelny_przeplyw_claim_v2_tylko_swoj_produkt(client, klient, marcin):
    u, f = marcin
    client.force_login(u)
    r, verifier = authorize(client, klient[0])
    assert r["Location"].startswith(REDIRECT)
    code = parse_qs(urlparse(r["Location"]).query)["code"][0]
    token = client.post("/o/token/", {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                      "client_id": klient[0], "client_secret": klient[1], "code_verifier": verifier}).json()
    c = jwt(token["id_token"])
    assert c["nonce"] == "n1" and c["preferred_username"] == "marcin@x.pl" and c["name"] == "Marcin"
    assert c["firmy"] == [{"id": str(f.id), "nazwa": "Sami Swoi", "wlasciciel": True, "produkty": {"kalendarz": "kierownik"}}]
    info = client.get("/o/userinfo/", HTTP_AUTHORIZATION=f"Bearer {token['access_token']}").json()
    assert info["firmy"][0]["produkty"] == {"kalendarz": "kierownik"}  # Grafik nie wycieka do Kalendarza


def test_zly_redirect_uri_i_brak_pkce_odrzucone(client, klient, marcin):
    client.force_login(marcin[0])
    r, _ = authorize(client, klient[0], redirect="https://zla.strona/oidc/callback/")
    assert r.status_code != 302
    r, _ = authorize(client, klient[0], pkce=False)
    assert "error" in r.get("Location", "error")


def test_rejestracja_klienta_idempotentna_i_tylko_dla_znanego_produktu(klient):
    err = io.StringIO()
    call_command("klient_oidc", "kalendarz", REDIRECT, stdout=io.StringIO(), stderr=err)
    assert "ma już klienta" in err.getvalue()
    with pytest.raises(CommandError):
        call_command("klient_oidc", "nieznany", REDIRECT, stdout=io.StringIO())
    assert Produkt.objects.get(kod="kalendarz").klient is not None
