"""Konto jako dostawca OpenID Connect. Kontrakt claimów v2 — docs/PROJEKT.md i uslugi.firmy_do_claimu."""
from django.http import JsonResponse
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.views import UserInfoView

from .uslugi import firmy_do_claimu


class Walidator(OAuth2Validator):
    oidc_claim_scope = {**OAuth2Validator.oidc_claim_scope, "firmy": "firmy", "preferred_username": "profile",
                        "email_verified": "email"}

    def get_additional_claims(self, request):
        u = request.user
        produkt = getattr(request.client, "produkt", None) if getattr(request, "client", None) else None
        return {
            "preferred_username": u.username,
            "name": u.get_full_name() or u.username,
            "email": u.email,
            # ponytail: e-mail potwierdzamy linkiem z zaproszenia/resetu; osobnej weryfikacji adresu w MVP nie ma
            "email_verified": True,
            "firmy": firmy_do_claimu(u, produkt),
        }


class UserInfo(UserInfoView):
    """RFC 9700 §4.3.2: token nigdy w adresie URL (logi, historia, Referer). DOT 3.4.1 sprawdza to w verify_request,
    ale userinfo idzie inną ścieżką (create_userinfo_response) — łatka do czasu poprawki w DOT (test: test_rfc9700)."""

    def dispatch(self, request, *args, **kwargs):
        if "access_token" in request.GET:
            r = JsonResponse({"error": "invalid_request", "error_description": "Token tylko w nagłówku Authorization."},
                             status=401)
            r["WWW-Authenticate"] = 'Bearer error="invalid_request"'
            return r
        return super().dispatch(request, *args, **kwargs)
