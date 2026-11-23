import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class Firma(models.Model):
    """Klient sudomie: restauracja, hotel, biuro. Jedna firma = wiele osób i produktów."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nazwa = models.CharField("nazwa", max_length=200)
    aktywna = models.BooleanField("aktywna", default=True)
    rejestracja = models.DateTimeField("czeka na potwierdzenie od", null=True, blank=True,
                                       help_text="Założona formularzem rejestracji; puste = potwierdzona albo założona przez nas.")
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "firmy"
        ordering = ["nazwa"]

    def __str__(self):
        return self.nazwa


class Produkt(models.Model):
    """Produkt pakietu (rejestr w produkty.json). Klient OIDC = aplikacja w django-oauth-toolkit."""
    kod = models.SlugField("kod", max_length=40, unique=True)
    nazwa = models.CharField("nazwa", max_length=80)
    adres = models.URLField("adres")
    role = models.JSONField("role", default=list, help_text="Pierwsza = najszersza.")
    klient = models.OneToOneField("oauth2_provider.Application", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="produkt")
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "produkty"
        ordering = ["nazwa"]

    def __str__(self):
        return self.nazwa


class Czlonkostwo(models.Model):
    """Osoba w firmie. Właściciel zarządza zespołem i dostępami."""
    firma = models.ForeignKey(Firma, on_delete=models.CASCADE, related_name="czlonkostwa")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="czlonkostwa")
    wlasciciel = models.BooleanField("właściciel", default=False)
    aktywne = models.BooleanField("aktywne", default=True)
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "członkostwa"
        constraints = [models.UniqueConstraint(fields=["firma", "user"], name="czlonkostwo_unikalne")]

    def __str__(self):
        return f"{self.user} @ {self.firma}"


class Dostep(models.Model):
    """Rola osoby w produkcie danej firmy. Brak wiersza = brak dostępu."""
    czlonkostwo = models.ForeignKey(Czlonkostwo, on_delete=models.CASCADE, related_name="dostepy")
    produkt = models.ForeignKey(Produkt, on_delete=models.PROTECT, related_name="dostepy")
    rola = models.CharField("rola", max_length=40)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "dostępy"
        constraints = [models.UniqueConstraint(fields=["czlonkostwo", "produkt"], name="dostep_unikalny")]

    def clean(self):
        if self.rola not in (self.produkt.role or []):
            raise ValidationError({"rola": f"{self.produkt.nazwa} nie zna roli „{self.rola}”."})

    def __str__(self):
        return f"{self.czlonkostwo} · {self.produkt.kod}={self.rola}"


class Zaproszenie(models.Model):
    """Link jednorazowy dla nowej osoby. Trzymamy tylko sha256 tokenu."""
    firma = models.ForeignKey(Firma, on_delete=models.CASCADE, related_name="zaproszenia")
    email = models.EmailField("e-mail")
    imie = models.CharField("imię", max_length=150, blank=True)
    dostepy = models.JSONField("dostępy", default=dict, help_text='{"kod_produktu": "rola"}')
    wlasciciel = models.BooleanField("jako właściciel", default=False)
    token_hash = models.CharField(max_length=64, unique=True)
    wazne_do = models.DateTimeField("ważne do")
    uzyte = models.DateTimeField("użyte", null=True, blank=True)
    zaprosil = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="+")
    utworzono = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "zaproszenia"

    def __str__(self):
        return f"{self.email} → {self.firma}"
