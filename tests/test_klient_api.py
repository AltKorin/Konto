"""Token aplikacji (client credentials) + introspekcja — kontrakt mostu Kalendarz → Grafik (#758)."""
import base64
import io

import pytest
from django.core.management import CommandError, call_command

from konto import uslugi


def env(out):
    return dict(l.split("=", 1) for l in out.getvalue().split() if "=" in l)


def basic(cid, sekret):
    return {"HTTP_AUTHORIZATION": "Basic " + base64.b64encode(f"{cid}:{sekret}".encode()).decode()}


@pytest.fixture
def klienci(db):
    uslugi.wczytaj_produkty()
    api, oidc = io.StringIO(), io.StringIO()
    call_command("klient_api", "grafik", stdout=api)
    call_command("klient_oidc", "kalendarz", "https://k.test/oidc/callback/", stdout=oidc)
    a, o = env(api), env(oidc)
    return (a["KONTO_API_CLIENT_ID"], a["KONTO_API_CLIENT_SECRET"]), (o["OIDC_CLIENT_ID"], o["OIDC_CLIENT_SECRET"])


def token(client, cid, sekret):
    r = client.post("/o/token/", {"grant_type": "client_credentials", "scope": "api"}, **basic(cid, sekret))
    return r


def test_token_aplikacji_i_introspekcja_klientem_kalendarza(client, klienci):
    (gid, gsek), (kid, ksek) = klienci
    r = token(client, gid, gsek)
    assert r.status_code == 200, r.content
    t = r.json()["access_token"]
    i = client.post("/o/introspect/", {"token": t}, **basic(kid, ksek)).json()
    assert i["active"] and i["client_id"] == gid and "api" in i["scope"].split()


def test_introspekcja_bez_uwierzytelnienia_odmawia(client, klienci):
    (gid, gsek), _ = klienci
    t = token(client, gid, gsek).json()["access_token"]
    assert client.post("/o/introspect/", {"token": t}).status_code in (401, 403)


def test_zly_sekret_nie_dostaje_tokenu(client, klienci):
    (gid, _), _ = klienci
    assert token(client, gid, "zly").status_code == 401


def test_klient_logowania_nie_dostaje_tokenu_aplikacji(client, klienci):
    _, (kid, ksek) = klienci
    assert token(client, kid, ksek).status_code in (400, 401)


def test_drugi_raz_nic_nie_tworzy(klienci):
    out, err = io.StringIO(), io.StringIO()
    call_command("klient_api", "grafik", stdout=out, stderr=err)
    assert out.getvalue() == "" and "nic nie zmieniono" in err.getvalue()


def test_nieznany_produkt(db):
    with pytest.raises(CommandError):
        call_command("klient_api", "nieznany", stdout=io.StringIO())
