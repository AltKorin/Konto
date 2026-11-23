import json
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.db import transaction
from django.views.decorators.http import require_POST
from inertia import location, render
from oauth2_provider.models import get_application_model

from . import poczta, uslugi
from .models import Czlonkostwo, Produkt

User = get_user_model()


def _json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


def _limit(klucz, limit, sekundy):
    """True = przekroczony. ponytail: licznik w cache (tabela w bazie), bez osobnego Redisa."""
    n = cache.get(klucz, 0) + 1
    cache.set(klucz, n, sekundy)
    return n > limit


def przejdz(request, url):
    """Po logowaniu: Inertia (XHR) nie może sama iść za łańcuchem /o/authorize/ → produkt (poszłoby w tle, bez ciasteczek
    produktu, i zużyłoby kod) — każemy przeglądarce przejść pełną nawigacją (409 + X-Inertia-Location)."""
    return location(url) if request.headers.get("X-Inertia") else redirect(url)


def bezpieczny_next(next_url):
    """Tylko ścieżki tego serwisu („/…”, nie „//obcy.pl”) — bez otwartego przekierowania."""
    n = str(next_url or "")
    return n if n.startswith("/") and not n.startswith("//") and "\\" not in n else "/"


def produkt_z_next(next_url):
    """Nazwa produktu, który wysłał do logowania (/o/authorize/?client_id=…) — do napisu na ekranie."""
    p = urlparse(next_url)
    if p.path != "/o/authorize/":
        return None
    cid = (parse_qs(p.query).get("client_id") or [""])[0]
    app = get_application_model().objects.filter(client_id=cid).select_related("produkt").first()
    return getattr(getattr(app, "produkt", None), "nazwa", None) if app else None


# ---------- logowanie ----------

def logowanie(request):
    nxt = bezpieczny_next(request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(nxt)
    bledy = {}
    if request.method == "POST":
        d = _json(request)
        email = str(d.get("email", "")).strip().lower()
        if _limit(f"log:{_ip(request)}", settings.LIMIT_LOGOWAN_NA_MINUTE, 60):
            bledy["haslo"] = "Za dużo prób. Odczekaj minutę i spróbuj ponownie."
        else:
            user = authenticate(request, username=email, password=str(d.get("haslo", "")))
            if user:
                login(request, user)
                return przejdz(request, nxt)
            bledy["haslo"] = "Zły e-mail albo hasło."
    return render(request, "Logowanie", {"bledy": bledy, "next": nxt, "produkt": produkt_z_next(nxt),
                                         "rejestracja": settings.REJESTRACJA_WLACZONA})


@require_POST
def wyloguj(request):
    logout(request)
    return redirect("logowanie")


# ---------- reset hasła ----------

def reset_hasla(request):
    if request.method == "POST":
        d = _json(request)
        if _limit(f"reset:{_ip(request)}", settings.LIMIT_RESETOW_NA_GODZINE, 3600):
            return render(request, "ResetHasla", {"wyslano": False, "blad": "Za dużo prób. Spróbuj za godzinę."})
        try:
            email = uslugi.normalizuj_email(d.get("email"))
        except uslugi.BladKonta as e:
            return render(request, "ResetHasla", {"wyslano": False, "blad": str(e)})
        user = User.objects.filter(username=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            link = request.build_absolute_uri(f"/nowe-haslo/{uid}/{default_token_generator.make_token(user)}/")
            poczta.wyslij_reset(email, link)
        # zawsze ta sama odpowiedź — nie zdradzamy, czy konto istnieje
        return render(request, "ResetHasla", {"wyslano": True, "blad": None})
    return render(request, "ResetHasla", {"wyslano": False, "blad": None})


def rejestracja(request):
    """„Załóż konto firmy” — dla każdego produktu rodziny (?produkt=kalendarz). Zawsze ta sama odpowiedź po wysłaniu:
    nie zdradzamy, czy adres ma już konto (link z maila działa w obu przypadkach)."""
    from django.http import Http404
    if not settings.REJESTRACJA_WLACZONA:
        raise Http404
    produkty = [{"kod": p.kod, "nazwa": p.nazwa} for p in Produkt.objects.exclude(role=[]).order_by("nazwa")]
    d = _json(request) if request.method == "POST" else {}
    wybrany = str(d.get("produkt") or request.GET.get("produkt") or "")
    props = {"produkty": produkty, "produkt": wybrany if any(p["kod"] == wybrany for p in produkty) else "",
             "wyslano": False, "bledy": {}}
    if request.method == "POST":
        if _limit(f"rejestracja:{_ip(request)}", settings.REJESTRACJA_NA_GODZINE, 3600):
            return render(request, "Rejestracja", {**props, "bledy": {"email": "Za dużo prób. Spróbuj za godzinę."}})
        try:
            z, token = uslugi.zarejestruj_firme(d.get("nazwa"), d.get("email"), d.get("imie"), wybrany)
        except uslugi.BladKonta as e:
            return render(request, "Rejestracja", {**props, "dane": d, "bledy": {"email": str(e)}})
        produkt = next(p["nazwa"] for p in produkty if p["kod"] == wybrany)
        poczta.wyslij_rejestracje(z, request.build_absolute_uri(f"/zaproszenie/{token}/"), produkt)
        return render(request, "Rejestracja", {**props, "wyslano": True})
    return render(request, "Rejestracja", props)


def nowe_haslo(request, uid, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if not user or not default_token_generator.check_token(user, token):
        return render(request, "NoweHaslo", {"wazny": False, "bledy": {}})
    bledy = {}
    if request.method == "POST":
        d = _json(request)
        haslo = str(d.get("haslo", ""))
        if haslo != str(d.get("powtorz", "")):
            bledy["powtorz"] = "Hasła się różnią."
        else:
            try:
                validate_password(haslo, user)
            except ValidationError as e:
                bledy["haslo"] = " ".join(e.messages)
        if not bledy:
            user.set_password(haslo)
            user.save()  # zmiana hasła unieważnia link (token zależy od hasha hasła)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Hasło zmienione. Jesteś zalogowany.")
            return redirect("start")
    return render(request, "NoweHaslo", {"wazny": True, "bledy": bledy, "email": user.username})


# ---------- zaproszenie ----------

def zaproszenie(request, token):
    try:
        z = uslugi.zaproszenie_po_tokenie(token)
    except uslugi.BladKonta as e:
        return render(request, "Zaproszenie", {"blad": str(e)})
    konto_istnieje = User.objects.filter(username=z.email).exists()
    bledy = {}
    if request.method == "POST":
        d = _json(request)
        try:
            if request.user.is_authenticated:
                user, _ = uslugi.przyjmij_zaproszenie(token, user=request.user)
            else:
                if str(d.get("haslo", "")) != str(d.get("powtorz", "")):
                    raise uslugi.BladKonta("Hasła się różnią.")
                user, _ = uslugi.przyjmij_zaproszenie(token, haslo=str(d.get("haslo", "")))
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Dołączyłeś do zespołu {z.firma.nazwa}.")
            return redirect("start")
        except uslugi.BladKonta as e:
            bledy["haslo"] = str(e)
    nazwy = dict(Produkt.objects.filter(kod__in=z.dostepy).values_list("kod", "nazwa"))
    return render(request, "Zaproszenie", {
        "blad": None, "bledy": bledy, "firma": z.firma.nazwa, "email": z.email, "imie": z.imie,
        "produkty": [{"nazwa": nazwy.get(k, k), "rola": r} for k, r in z.dostepy.items()],
        "konto_istnieje": konto_istnieje, "zalogowany_jako": request.user.username if request.user.is_authenticated else None,
    })


# ---------- start (Moje konto — rozbudowa w #764) ----------

@login_required
def start(request):
    firmy = []
    for c in Czlonkostwo.objects.filter(user=request.user, aktywne=True, firma__aktywna=True) \
            .select_related("firma").prefetch_related("dostepy__produkt").order_by("firma__nazwa"):
        firmy.append({"id": str(c.firma_id), "nazwa": c.firma.nazwa, "wlasciciel": c.wlasciciel,
                      "produkty": [{"kod": d.produkt.kod, "nazwa": d.produkt.nazwa, "adres": d.produkt.adres, "rola": d.rola}
                                   for d in c.dostepy.all()]})
    return render(request, "Start", {"firmy": firmy})


# ---------- zespół firmy (#764) ----------
from functools import wraps  # noqa: E402

from django.http import Http404  # noqa: E402
from django.shortcuts import get_object_or_404  # noqa: E402

from .models import Zaproszenie  # noqa: E402


def tylko_wlasciciel(widok):
    """Firma tylko dla jej właściciela; dla innych 404 — bez zdradzania, że taka firma istnieje."""
    @wraps(widok)
    def opakowany(request, firma_id, *a, **kw):
        firma = uslugi.firma_wlasciciela(request.user, firma_id)
        if not firma:
            raise Http404
        return widok(request, firma, *a, **kw)
    return login_required(opakowany)


def _produkty():
    return [{"kod": p.kod, "nazwa": p.nazwa, "role": p.role} for p in Produkt.objects.order_by("nazwa")]


def _link_zaproszenia(request, token):
    return request.build_absolute_uri(f"/zaproszenie/{token}/")


@tylko_wlasciciel
def zespol(request, firma):
    return render(request, "Zespol", {"firma": {"id": str(firma.id), "nazwa": firma.nazwa}, "produkty": _produkty(),
                                      "ja": request.user.pk, **uslugi.zespol(firma)})


def _wroc(firma):
    return redirect("zespol", firma_id=firma.id)


@tylko_wlasciciel
@require_POST
def zespol_zapros(request, firma):
    d = _json(request)
    try:
        z, token = uslugi.zapros(firma, d.get("email"), {k: r for k, r in (d.get("dostepy") or {}).items() if r},
                                 zaprosil=request.user, imie=d.get("imie", ""), wlasciciel=bool(d.get("wlasciciel")))
        poczta.wyslij_zaproszenie(z, _link_zaproszenia(request, token), request.user.get_full_name() or request.user.username)
        messages.success(request, f"Wysłano zaproszenie do {z.email}.")
    except uslugi.BladKonta as e:
        messages.error(request, str(e))
    return _wroc(firma)


@tylko_wlasciciel
@require_POST
def zespol_osoba(request, firma, czlonkostwo_id):
    c = get_object_or_404(Czlonkostwo, pk=czlonkostwo_id, firma=firma)
    d = _json(request)
    try:
        with transaction.atomic():
            if "dostepy" in d:
                uslugi.zmien_dostepy(c, d["dostepy"] or {})
            if "wlasciciel" in d:
                uslugi.ustaw_wlasciciela(c, bool(d["wlasciciel"]))
            if "aktywne" in d:
                uslugi.ustaw_aktywne(c, bool(d["aktywne"]))
        messages.success(request, f"Zapisano: {c.user.first_name or c.user.username}.")
    except uslugi.BladKonta as e:
        messages.error(request, str(e))
    return _wroc(firma)


@tylko_wlasciciel
@require_POST
def zespol_zaproszenie(request, firma, zaproszenie_id, akcja):
    z = get_object_or_404(Zaproszenie, pk=zaproszenie_id, firma=firma)
    try:
        if akcja == "anuluj":
            uslugi.anuluj_zaproszenie(z)
            messages.success(request, f"Anulowano zaproszenie dla {z.email}.")
        elif akcja == "wyslij":
            token = uslugi.odnow_zaproszenie(z)
            poczta.wyslij_zaproszenie(z, _link_zaproszenia(request, token), request.user.get_full_name() or request.user.username)
            messages.success(request, f"Wysłano ponownie do {z.email} (poprzedni link już nie działa).")
        else:
            raise Http404
    except uslugi.BladKonta as e:
        messages.error(request, str(e))
    return _wroc(firma)


@tylko_wlasciciel
@require_POST
def firma_nazwa(request, firma):
    try:
        uslugi.zmien_nazwe_firmy(firma, _json(request).get("nazwa"))
        messages.success(request, "Zmieniono nazwę firmy.")
    except uslugi.BladKonta as e:
        messages.error(request, str(e))
    return _wroc(firma)


# ---------- moje konto ----------

@login_required
def moje_konto(request):
    bledy = {}
    if request.method == "POST":
        d = _json(request)
        try:
            if d.get("co") == "haslo":
                uslugi.zmien_haslo(request.user, d.get("obecne"), d.get("nowe"), d.get("powtorz"))
                update_session_auth_hash(request, request.user)  # zostajesz zalogowany na tym urządzeniu
                messages.success(request, "Hasło zmienione.")
            else:
                uslugi.zmien_moje_dane(request.user, d.get("imie"), d.get("email"), d.get("haslo_obecne"))
                messages.success(request, "Zapisano.")
            return redirect("moje_konto")
        except uslugi.BladKonta as e:
            bledy[d.get("co") or "dane"] = str(e)
    return render(request, "MojeKonto", {"bledy": bledy, "dane": {"imie": request.user.first_name, "email": request.user.username}})
