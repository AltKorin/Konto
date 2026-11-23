from django.contrib import admin
from django.http import HttpResponse
from konto.oidc import UserInfo
from django.urls import include, path

from konto import views as v

urlpatterns = [
    path("zdrowie/", lambda r: HttpResponse("ok")),
    path("serwis/", admin.site.urls),
    path("o/userinfo/", UserInfo.as_view(), name="userinfo"),  # przed DOT: łatka RFC 9700 (konto/oidc.py)
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("", v.start, name="start"),
    path("logowanie/", v.logowanie, name="logowanie"),
    path("wyloguj/", v.wyloguj, name="wyloguj"),
    path("reset-hasla/", v.reset_hasla, name="reset_hasla"),
    path("rejestracja/", v.rejestracja, name="rejestracja"),
    path("nowe-haslo/<str:uid>/<str:token>/", v.nowe_haslo, name="nowe_haslo"),
    path("zaproszenie/<str:token>/", v.zaproszenie, name="zaproszenie"),
    path("moje-konto/", v.moje_konto, name="moje_konto"),
    path("firma/<uuid:firma_id>/zespol/", v.zespol, name="zespol"),
    path("firma/<uuid:firma_id>/zapros/", v.zespol_zapros, name="zespol_zapros"),
    path("firma/<uuid:firma_id>/osoba/<int:czlonkostwo_id>/", v.zespol_osoba, name="zespol_osoba"),
    path("firma/<uuid:firma_id>/zaproszenie/<int:zaproszenie_id>/<str:akcja>/", v.zespol_zaproszenie, name="zespol_zaproszenie"),
    path("firma/<uuid:firma_id>/nazwa/", v.firma_nazwa, name="firma_nazwa"),
]
