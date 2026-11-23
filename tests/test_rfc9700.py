"""RFC 9700 (OAuth 2.0 Security BCP, #774): czego dostawca NIE może przyjąć. Ustawienia w config/settings.py."""
import base64
from urllib.parse import parse_qs, urlparse

from oauth2_provider.models import AccessToken

from test_oidc import REDIRECT, authorize, klient, marcin  # noqa: F401  (fixtures)


def zaloguj_i_token(client, klient, marcin):
    client.force_login(marcin[0])
    r, verifier = authorize(client, klient[0])
    q = parse_qs(urlparse(r["Location"]).query)
    token = client.post("/o/token/", {"grant_type": "authorization_code", "code": q["code"][0], "redirect_uri": REDIRECT,
                                      "client_id": klient[0], "client_secret": klient[1], "code_verifier": verifier}).json()
    return q, token


def test_odpowiedz_autoryzacji_niesie_iss(client, klient, marcin):
    q, _ = zaloguj_i_token(client, klient, marcin)
    assert q["iss"][0].endswith("/o")


def test_token_w_bazie_tylko_jako_skrot(client, klient, marcin):
    _, token = zaloguj_i_token(client, klient, marcin)
    assert not AccessToken.objects.filter(token=token["access_token"]).exists()
    assert client.get("/o/userinfo/", HTTP_AUTHORIZATION=f"Bearer {token['access_token']}").status_code == 200


def test_token_w_adresie_url_odrzucony(client, klient, marcin):
    _, token = zaloguj_i_token(client, klient, marcin)
    assert client.get("/o/userinfo/", {"access_token": token["access_token"]}).status_code == 401


def test_password_grant_odrzucony(client, klient, marcin):
    basic = base64.b64encode(f"{klient[0]}:{klient[1]}".encode()).decode()
    r = client.post("/o/token/", {"grant_type": "password", "username": "marcin@x.pl",
                                  "password": "dlugie-haslo-do-testow-1"}, HTTP_AUTHORIZATION=f"Basic {basic}")
    assert r.status_code in (400, 401) and "access_token" not in r.json()


def test_pkce_plain_odrzucone(client, klient, marcin):
    client.force_login(marcin[0])
    r = client.get("/o/authorize/", {"client_id": klient[0], "response_type": "code", "redirect_uri": REDIRECT,
                                     "scope": "openid", "state": "s", "code_challenge": "x" * 43,
                                     "code_challenge_method": "plain"})
    assert "code=" not in r.get("Location", "")


def test_implicit_grant_odrzucony(client, klient, marcin):
    client.force_login(marcin[0])
    r = client.get("/o/authorize/", {"client_id": klient[0], "response_type": "token", "redirect_uri": REDIRECT,
                                     "scope": "openid", "state": "s"})
    assert "access_token=" not in r.get("Location", "")
