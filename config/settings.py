"""Konto sudomie — jeden login dla całego pakietu (docs/PROJEKT.md). Konfiguracja z .env, nie z kodu."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TESTING = "pytest" in sys.modules or "test" in sys.argv


def env(nazwa, domyslnie=""):
    return os.environ.get(nazwa, domyslnie)


DEBUG = env("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-tylko-lokalnie-nie-na-produkcje")
if not DEBUG and SECRET_KEY.startswith("dev-"):
    raise RuntimeError("Ustaw DJANGO_SECRET_KEY w .env produkcji.")
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h] + ["localhost"]
CSRF_TRUSTED_ORIGINS = [h for h in env("DJANGO_CSRF_TRUSTED_ORIGINS").split(",") if h]

INSTALLED_APPS = [
    "jazzmin",  # MUSI być przed django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_history",
    "oauth2_provider",
    "core_audit",
    "django_vite",
    "inertia",
    "konto",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",  # PO AuthenticationMiddleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "inertia.middleware.InertiaMiddleware",
    "konto.middleware.WspolneDaneMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": Path(env("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))),
    # ponytail: SQLite wystarczy dla logowań małych firm; Postgres, gdy zapisy zaczną się blokować
    "OPTIONS": {"timeout": 10, "init_command": "PRAGMA journal_mode=WAL;"},
}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/logowanie/"

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "dist"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# własne nazwy ciasteczek: produkty pakietu na tym samym hoście (dev) nie nadpisują sobie sesji
SESSION_COOKIE_NAME = "konto_sesja"
CSRF_COOKIE_NAME = "XSRF-TOKEN"
CSRF_HEADER_NAME = "HTTP_X_XSRF_TOKEN"
SESSION_COOKIE_AGE = int(env("SESSION_DNI", "30")) * 86400

if not DEBUG:
    # za nginx/Cloudflare Tunnel: oba razem albo żadne (pętla przekierowań — CLAUDE.md)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env("DJANGO_SSL_REDIRECT", "1") == "1"
    SECURE_REDIRECT_EXEMPT = [r"^zdrowie/$"]  # healthcheck Dockera po HTTP na localhost
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    # HSTS tylko dla konto.sudomie.pl (bez includeSubDomains/preload — inne subdomeny rodziny decydują same). Zaczynamy od doby;
    # podniesienie = zmiana DJANGO_HSTS_SEKUNDY w .env (np. 31536000), 0 = wyłączone.
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SEKUNDY", "86400"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # dotyczy tylko *.konto.sudomie.pl (nie ma takich), nie reszty sudomie.pl
    SILENCED_SYSTEM_CHECKS = ["security.W021"]  # preload jest dla domen głównych, nie dla subdomeny

# Zaproszenie (link jednorazowy) ważne tyle dni
ZAPROSZENIE_DNI = int(env("ZAPROSZENIE_DNI", "7"))
# GA4 tylko na ekranach publicznych (logowanie, reset hasła, zaproszenie, rejestracja) — jedna usługa dla całej rodziny
# sudomie, Consent Mode v2 (frontend/src/lib/zgoda.ts). Puste = brak tagu.
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID").strip()
if GA_MEASUREMENT_ID and not __import__("re").fullmatch(r"G-[A-Z0-9]{4,20}", GA_MEASUREMENT_ID):
    raise RuntimeError("GA_MEASUREMENT_ID musi wyglądać jak G-XXXXXXXXXX")
# Rejestracja firm przez formularz (flaga: 0 = strony /rejestracja/ nie ma). Limity: na IP/godz., oczekujących naraz.
REJESTRACJA_WLACZONA = env("REJESTRACJA_WLACZONA", "0") == "1"
REJESTRACJA_NA_GODZINE = int(env("REJESTRACJA_NA_GODZINE", "5"))
REJESTRACJA_MAX_OCZEKUJACYCH = int(env("REJESTRACJA_MAX_OCZEKUJACYCH", "200"))


# ---------- dostawca OpenID Connect (kod przeniesiony z gałęzi sso-oidc Grafiku) ----------

def _klucz_oidc():
    plik = env("OIDC_KLUCZ_PLIK")
    if plik and Path(plik).exists():
        return Path(plik).read_text()
    if not (DEBUG or TESTING):
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("Produkcja wymaga OIDC_KLUCZ_PLIK (klucz RSA w PEM, deploy/oidc-klucz.sh)")
    from jwcrypto import jwk  # dev/testy: klucz jednorazowy
    return jwk.JWK.generate(kty="RSA", size=2048).export_to_pem(private_key=True, password=None).decode()


OAUTH2_PROVIDER_APPLICATION_MODEL = "oauth2_provider.Application"  # Produkt.klient → swappable model DOT
OAUTH2_PROVIDER = {
    "OIDC_ENABLED": True,
    "OIDC_RSA_PRIVATE_KEY": _klucz_oidc(),
    "PKCE_REQUIRED": True,
    "SCOPES": {
        "openid": "Logowanie",
        "profile": "Imię i login",
        "email": "Adres e-mail",
        "firmy": "Firmy i rola w produkcie",
        "api": "Dostęp aplikacji do API (serwer–serwer)",
    },
    "DEFAULT_SCOPES": ["openid"],
    "OAUTH2_VALIDATOR_CLASS": "konto.oidc.Walidator",
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "OIDC_RP_INITIATED_LOGOUT_ENABLED": True,
    "OIDC_RP_INITIATED_LOGOUT_ALWAYS_PROMPT": False,
    # RFC 9700 (OAuth 2.0 Security BCP), #774 — domyślne w DOT 4.0, włączone wcześniej. Produkty używają tylko:
    # authorization code + PKCE S256 (logowanie, core_sso) i client credentials (API serwer–serwer, klient_api).
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,        # bez implicit grant
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,        # bez hasła użytkownika przez API tokenów
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,           # tylko S256, bez "plain"
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,  # token tylko w nagłówku, nigdy w URL (logi, Referer)
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,    # parametr iss w odpowiedzi autoryzacji (RFC 9207)
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,         # tokeny w bazie tylko jako skrót (suma kontrolna i tak jest)
    "REFRESH_TOKEN_REUSE_PROTECTION": True,              # powtórzony refresh token unieważnia całą rodzinę
    "COMPLIANT_BCP_RFC9700_REFRESH_TOKEN": True,
    # http tylko przy pracy lokalnej (redirect na 127.0.0.1); produkcja wyłącznie https
    "ALLOWED_REDIRECT_URI_SCHEMES": ["https", "http"] if DEBUG else ["https"],
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_SCHEME": True,
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_MATCHING": True,
    "COMPLIANT_BCP_RFC9700_PKCE_REQUIRED": True,
}

JAZZMIN_SETTINGS = {
    "site_title": "Konto sudomie — serwis",
    "site_header": "Konto sudomie",
    "site_brand": "Konto (serwis)",
    "welcome_sign": "Panel serwisowy — klienci pracują w panelu /",
}

LOGGING = {"version": 1, "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "INFO"}}

# Poczta systemowa całej rodziny (CLAUDE.md): no-reply@sudomie.pl przez mail.sudomie.pl:465.
# Django 6.1: MAILERS zamiast przestarzałych EMAIL_* (usuwane w 2028).
MAILERS = {"default": (
    {"BACKEND": "django.core.mail.backends.console.EmailBackend"} if DEBUG and not env("EMAIL_HOST_PASSWORD") else
    {"BACKEND": "django.core.mail.backends.smtp.EmailBackend", "OPTIONS": {
        "host": env("EMAIL_HOST", "mail.sudomie.pl"),
        "port": int(env("EMAIL_PORT", "465")),
        "use_ssl": env("EMAIL_USE_SSL", "1") == "1",
        "username": env("EMAIL_HOST_USER", "no-reply@sudomie.pl"),
        "password": env("EMAIL_HOST_PASSWORD"),
        "timeout": 15,
    }}
)}
if TESTING:
    MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Konto sudomie <no-reply@sudomie.pl>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Inertia + Vite (jak Kalendarz)
INERTIA_LAYOUT = "base.html"
DJANGO_VITE = {"default": {
    "dev_mode": env("VITE_DEV", "1" if DEBUG else "0") == "1",
    "dev_server_port": 5174,
    "manifest_path": BASE_DIR / "frontend" / "dist" / "manifest.json",
}}

# Licznik prób logowania/resetu wspólny dla workerów gunicorna (tabela: manage.py createcachetable)
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "cache_konto"}}
if TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
LIMIT_LOGOWAN_NA_MINUTE = int(env("LIMIT_LOGOWAN_NA_MINUTE", "10"))
LIMIT_RESETOW_NA_GODZINE = int(env("LIMIT_RESETOW_NA_GODZINE", "5"))
