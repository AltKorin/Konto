from django.conf import settings
from django.contrib import messages
from django.middleware.csrf import get_token
from inertia import share


class WspolneDaneMiddleware:
    """Na każdej stronie: zalogowana osoba i komunikaty po akcji. get_token → ciasteczko XSRF-TOKEN dla axios (Inertia)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        get_token(request)
        share(request,
              osoba=lambda: ({"imie": request.user.first_name, "email": request.user.username}
                             if request.user.is_authenticated else None),
              ga=lambda: settings.GA_MEASUREMENT_ID,
              komunikaty=lambda: [{"tekst": str(m), "poziom": m.level_tag} for m in messages.get_messages(request)])
        return self.get_response(request)
