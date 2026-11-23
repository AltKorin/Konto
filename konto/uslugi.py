"""Serwisy Konta — UI, admin i komendy wołają tylko te funkcje.

Prawa (testy: tests/test_konto_laws.py):
- claim `firmy` zawiera tylko aktywne członkostwa w aktywnych firmach; brak Dostępu = brak klucza produktu,
- klient OIDC przypięty do produktu widzi tylko firmy z dostępem do SWOJEGO produktu i tylko swój klucz (minimalizacja),
- rola zawsze należy do listy ról produktu (inaczej błąd, nic się nie zapisuje),
- zaproszenie jest jednorazowe: drugie użycie, wygaśnięcie albo zły token → błąd, bez zmian w danych,
- przyjęcie zaproszenia jest idempotentne względem członkostwa (istniejąca osoba nie dostaje drugiego członkostwa),
- login = e-mail małymi literami (Marcin@X.pl i marcin@x.pl to jedno konto),
- rejestracja firmy niczego nie daje przed kliknięciem linku: firma bez członków, nikt nie dostaje claimu; porzucona
  (link wygasł) znika przy kolejnej rejestracji; firmy założone przez nas (bez `rejestracja`) nigdy nie są sprzątane.
"""
import hashlib
import json
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .models import Czlonkostwo, Dostep, Firma, Produkt, Zaproszenie


class BladKonta(Exception):
    """Błąd do pokazania użytkownikowi (po polsku, bez szczegółów technicznych)."""


# ---------- produkty ----------

def wczytaj_produkty(plik=None):
    """produkty.json → Produkt (tworzy/aktualizuje nazwę, adres, role). Idempotentne."""
    dane = json.loads(Path(plik or settings.BASE_DIR / "produkty.json").read_text(encoding="utf-8"))
    zmienione = []
    for kod, p in dane.items():
        if kod.startswith("_"):
            continue
        if not p.get("role"):
            raise BladKonta(f"Produkt {kod}: pusta lista ról.")
        _, utworzony = Produkt.objects.update_or_create(
            kod=kod, defaults={"nazwa": p["nazwa"], "adres": p["adres"], "role": list(p["role"])})
        zmienione.append((kod, utworzony))
    return zmienione


# ---------- claimy OIDC ----------

def firmy_do_claimu(user, produkt=None):
    """Kontrakt v2 (docs/PROJEKT.md): [{"id", "nazwa", "wlasciciel", "produkty": {kod: rola}}]."""
    wynik = []
    czl = (Czlonkostwo.objects.filter(user=user, aktywne=True, firma__aktywna=True)
           .select_related("firma").prefetch_related("dostepy__produkt").order_by("firma__nazwa"))
    for c in czl:
        produkty = {d.produkt.kod: d.rola for d in c.dostepy.all() if produkt is None or d.produkt_id == produkt.pk}
        if produkt is not None and not produkty:
            continue  # ten produkt nie musi wiedzieć o firmach, w których osoba go nie używa
        wynik.append({"id": str(c.firma_id), "nazwa": c.firma.nazwa, "wlasciciel": c.wlasciciel, "produkty": produkty})
    return wynik


# ---------- dostępy ----------

def ustaw_dostep(czlonkostwo, kod_produktu, rola):
    """Rola w produkcie; rola=None/'' zabiera dostęp. Zwraca Dostep albo None."""
    produkt = Produkt.objects.filter(kod=kod_produktu).first()
    if not produkt:
        raise BladKonta(f"Nie ma produktu „{kod_produktu}”.")
    if not rola:
        Dostep.objects.filter(czlonkostwo=czlonkostwo, produkt=produkt).delete()
        return None
    if rola not in produkt.role:
        raise BladKonta(f"{produkt.nazwa} nie zna roli „{rola}”. Dostępne: {', '.join(produkt.role)}.")
    d, _ = Dostep.objects.update_or_create(czlonkostwo=czlonkostwo, produkt=produkt, defaults={"rola": rola})
    return d


def _sprawdz_dostepy(dostepy):
    if not isinstance(dostepy, dict):
        raise BladKonta("Dostępy muszą być słownikiem produkt → rola.")
    produkty = {p.kod: p for p in Produkt.objects.filter(kod__in=dostepy.keys())}
    for kod, rola in dostepy.items():
        if kod not in produkty:
            raise BladKonta(f"Nie ma produktu „{kod}”.")
        if rola not in produkty[kod].role:
            raise BladKonta(f"{produkty[kod].nazwa} nie zna roli „{rola}”.")


# ---------- konta ----------

def normalizuj_email(email):
    email = str(email or "").strip().lower()
    try:
        validate_email(email)
        # RFC 5321: całość ≤ 254, część przed @ ≤ 64 (walidator Django tego nie pilnuje, SQLite też nie)
        if len(email) > 254 or len(email.split("@")[0]) > 64:
            raise ValidationError("za długi")
    except ValidationError:
        raise BladKonta("Podaj poprawny adres e-mail.")
    return email


def zaloz_firme(nazwa, wlasciciel_user):
    nazwa = str(nazwa or "").strip()
    if not nazwa:
        raise BladKonta("Podaj nazwę firmy.")
    with transaction.atomic():
        f = Firma.objects.create(nazwa=nazwa[:200])
        Czlonkostwo.objects.create(firma=f, user=wlasciciel_user, wlasciciel=True)
    return f


# ---------- zaproszenia ----------

def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def zapros(firma, email, dostepy, zaprosil=None, imie="", wlasciciel=False):
    """Tworzy zaproszenie. Zwraca (zaproszenie, token) — token pokazujemy/wysyłamy RAZ."""
    email = normalizuj_email(email)
    _sprawdz_dostepy(dostepy)
    if Czlonkostwo.objects.filter(firma=firma, user__username=email).exists():
        raise BladKonta(f"{email} już jest w zespole — zmień tej osobie dostępy w tabeli.")
    # jedno oczekujące zaproszenie na adres: nowe zastępuje stare (stary link przestaje działać)
    Zaproszenie.objects.filter(firma=firma, email=email, uzyte__isnull=True).delete()
    token = secrets.token_urlsafe(32)
    z = Zaproszenie.objects.create(
        firma=firma, email=email, imie=str(imie or "")[:150], dostepy=dostepy, wlasciciel=wlasciciel,
        token_hash=_hash(token), wazne_do=timezone.now() + timedelta(days=settings.ZAPROSZENIE_DNI), zaprosil=zaprosil)
    return z, token


def zaproszenie_po_tokenie(token):
    z = Zaproszenie.objects.select_related("firma").filter(token_hash=_hash(str(token or ""))).first()
    if not z or z.uzyte or z.wazne_do < timezone.now() or not z.firma.aktywna:
        raise BladKonta("To zaproszenie jest nieważne albo już zostało użyte. Poproś o nowe.")
    return z


def przyjmij_zaproszenie(token, haslo=None, user=None):
    """Nowa osoba podaje hasło (konto z e-mailem z zaproszenia) albo zalogowana osoba dołącza swoim kontem."""
    User = get_user_model()
    with transaction.atomic():
        z = zaproszenie_po_tokenie(token)
        z = Zaproszenie.objects.select_for_update().get(pk=z.pk)  # dwa równoległe kliknięcia = jedno użycie
        if z.uzyte:
            raise BladKonta("To zaproszenie zostało już użyte.")
        if user is None:
            user = User.objects.filter(username=z.email).first()
            if user:
                raise BladKonta("Masz już konto z tym adresem — zaloguj się i otwórz link jeszcze raz.")
            user = User(username=z.email, email=z.email, first_name=z.imie)
            try:
                validate_password(haslo or "", user)
            except ValidationError as e:
                raise BladKonta(" ".join(e.messages))
            user.set_password(haslo)
            user.save()
        c, _ = Czlonkostwo.objects.get_or_create(firma=z.firma, user=user, defaults={"wlasciciel": z.wlasciciel})
        if not c.aktywne or (z.wlasciciel and not c.wlasciciel):
            c.aktywne, c.wlasciciel = True, c.wlasciciel or z.wlasciciel
            c.save()
        for kod, rola in z.dostepy.items():
            ustaw_dostep(c, kod, rola)
        z.uzyte = timezone.now()
        z.save(update_fields=["uzyte"])
        if z.firma.rejestracja and z.wlasciciel:
            z.firma.rejestracja = None  # właściciel potwierdził adres — firma jest prawdziwa
            z.firma.save(update_fields=["rejestracja"])
    return user, c


# ---------- zespół firmy (#764) ----------
# Prawa (tests/test_zespol.py):
# - firma ma zawsze ≥ 1 aktywnego właściciela (odebranie roli / wyłączenie ostatniego = błąd, nic się nie zmienia),
# - zmiana dostępów jest atomowa: jedna zła rola → żadna zmiana,
# - wyłączona osoba znika z claimów (żaden produkt jej nie wpuści), włączenie przywraca dostępy,
# - anulowane zaproszenie przestaje działać; ponowne wysłanie unieważnia stary link,
# - tylko właściciel zarządza zespołem; dla innych firma „nie istnieje” (404, bez wycieku).

def firma_wlasciciela(user, firma_id):
    """Firma, w której user jest aktywnym właścicielem, albo None (widok zwraca wtedy 404)."""
    c = Czlonkostwo.objects.select_related("firma").filter(
        user=user, firma_id=firma_id, aktywne=True, wlasciciel=True, firma__aktywna=True).first()
    return c.firma if c else None


def _aktywni_wlasciciele(firma):
    return Czlonkostwo.objects.filter(firma=firma, aktywne=True, wlasciciel=True)


def zmien_dostepy(czlonkostwo, dostepy):
    """{kod: rola | ""} — puste = zabranie dostępu. Najpierw walidacja wszystkiego, potem zapis w jednej transakcji."""
    if not isinstance(dostepy, dict):
        raise BladKonta("Dostępy muszą być słownikiem produkt → rola.")
    _sprawdz_dostepy({k: r for k, r in dostepy.items() if r})
    nieznane = set(dostepy) - set(Produkt.objects.values_list("kod", flat=True))
    if nieznane:
        raise BladKonta(f"Nie ma produktu „{sorted(nieznane)[0]}”.")
    with transaction.atomic():
        for kod, rola in dostepy.items():
            ustaw_dostep(czlonkostwo, kod, rola or "")


def ustaw_wlasciciela(czlonkostwo, wlasciciel):
    with transaction.atomic():
        c = Czlonkostwo.objects.select_for_update().get(pk=czlonkostwo.pk)
        if c.wlasciciel and not wlasciciel and _aktywni_wlasciciele(c.firma).exclude(pk=c.pk).count() == 0:
            raise BladKonta("Firma musi mieć co najmniej jednego właściciela. Najpierw nadaj tę rolę komuś innemu.")
        c.wlasciciel = bool(wlasciciel)
        c.save(update_fields=["wlasciciel"])
    return c


def ustaw_aktywne(czlonkostwo, aktywne):
    with transaction.atomic():
        c = Czlonkostwo.objects.select_for_update().get(pk=czlonkostwo.pk)
        if not aktywne and c.wlasciciel and c.aktywne and _aktywni_wlasciciele(c.firma).exclude(pk=c.pk).count() == 0:
            raise BladKonta("Nie można wyłączyć ostatniego właściciela firmy.")
        c.aktywne = bool(aktywne)
        c.save(update_fields=["aktywne"])
    return c


def zmien_nazwe_firmy(firma, nazwa):
    nazwa = str(nazwa or "").strip()
    if not nazwa:
        raise BladKonta("Podaj nazwę firmy.")
    if len(nazwa) > 200:
        raise BladKonta("Nazwa może mieć najwyżej 200 znaków.")
    firma.nazwa = nazwa
    firma.save(update_fields=["nazwa"])
    return firma


def anuluj_zaproszenie(zaproszenie):
    if zaproszenie.uzyte:
        raise BladKonta("To zaproszenie zostało już przyjęte — zmień dostępy tej osoby w zespole.")
    zaproszenie.delete()


def odnow_zaproszenie(zaproszenie):
    """Nowy link (stary przestaje działać) i nowy termin. Zwraca token do wysłania."""
    if zaproszenie.uzyte:
        raise BladKonta("To zaproszenie zostało już przyjęte.")
    token = secrets.token_urlsafe(32)
    zaproszenie.token_hash = _hash(token)
    zaproszenie.wazne_do = timezone.now() + timedelta(days=settings.ZAPROSZENIE_DNI)
    zaproszenie.save(update_fields=["token_hash", "wazne_do"])
    return token


def zespol(firma):
    """Dane ekranu Zespół: osoby z dostępami + oczekujące zaproszenia."""
    osoby = []
    for c in (Czlonkostwo.objects.filter(firma=firma).select_related("user").prefetch_related("dostepy__produkt")
              .order_by("-aktywne", "-wlasciciel", "user__first_name", "user__username")):
        osoby.append({"id": c.pk, "imie": c.user.first_name, "email": c.user.username, "wlasciciel": c.wlasciciel,
                      "aktywne": c.aktywne, "dostepy": {d.produkt.kod: d.rola for d in c.dostepy.all()},
                      "ostatnio": c.user.last_login.strftime("%d.%m.%Y %H:%M") if c.user.last_login else None})
    zaproszenia = [{"id": z.pk, "email": z.email, "imie": z.imie, "dostepy": z.dostepy, "wlasciciel": z.wlasciciel,
                    "wazne_do": z.wazne_do.strftime("%d.%m.%Y"), "wygaslo": z.wazne_do < timezone.now()}
                   for z in firma.zaproszenia.filter(uzyte__isnull=True).order_by("-utworzono")]
    return {"osoby": osoby, "zaproszenia": zaproszenia}


# ---------- moje konto ----------

def zmien_moje_dane(user, imie, email=None, haslo_obecne=None):
    """Imię zawsze; e-mail (= login) tylko z obecnym hasłem i gdy wolny."""
    user.first_name = str(imie or "").strip()[:150]
    if email is not None and str(email).strip().lower() != user.username:
        nowy = normalizuj_email(email)
        if not user.check_password(haslo_obecne or ""):
            raise BladKonta("Żeby zmienić e-mail, podaj obecne hasło.")
        if get_user_model().objects.filter(username=nowy).exclude(pk=user.pk).exists():
            raise BladKonta("Ten e-mail jest już używany przez inne konto.")
        user.username = user.email = nowy
    user.save()
    return user


def zmien_haslo(user, obecne, nowe, powtorz):
    if not user.check_password(obecne or ""):
        raise BladKonta("Obecne hasło się nie zgadza.")
    if nowe != powtorz:
        raise BladKonta("Nowe hasła się różnią.")
    try:
        validate_password(nowe or "", user)
    except ValidationError as e:
        raise BladKonta(" ".join(e.messages))
    user.set_password(nowe)
    user.save()
    return user


# ---------- rejestracja firmy (#767 Konta; pierwszy klient: kalendarz.sudomie.pl) ----------

def sprzatnij_rejestracje():
    """Porzucone rejestracje (link wygasł, nikt nie dołączył) — razem z zaproszeniami."""
    teraz = timezone.now()
    Firma.objects.filter(rejestracja__isnull=False, czlonkostwa__isnull=True) \
        .exclude(zaproszenia__wazne_do__gte=teraz).delete()


def zarejestruj_firme(nazwa, email, imie, kod_produktu):
    """Formularz „Załóż konto firmy”: firma + zaproszenie właściciela z najszerszą rolą w wybranym produkcie.
    Zwraca (zaproszenie, token) — link idzie mailem. Ten sam adres ponownie = poprzednia rejestracja zastąpiona."""
    nazwa = str(nazwa or "").strip()
    if not nazwa:
        raise BladKonta("Podaj nazwę firmy.")
    email = normalizuj_email(email)
    produkt = Produkt.objects.filter(kod=str(kod_produktu or "")).first()
    if not produkt or not produkt.role:
        raise BladKonta("Wybierz aplikację, od której zaczynasz.")
    sprzatnij_rejestracje()
    if Firma.objects.filter(rejestracja__isnull=False).count() >= settings.REJESTRACJA_MAX_OCZEKUJACYCH:
        raise BladKonta("Za dużo rejestracji naraz — spróbuj za godzinę.")  # backpressure, nie kolejka
    with transaction.atomic():
        Firma.objects.filter(rejestracja__isnull=False, czlonkostwa__isnull=True,
                             zaproszenia__email=email, zaproszenia__uzyte__isnull=True).delete()
        firma = Firma.objects.create(nazwa=nazwa[:200], rejestracja=timezone.now())
        return zapros(firma, email, {produkt.kod: produkt.role[0]}, imie=imie, wlasciciel=True)
