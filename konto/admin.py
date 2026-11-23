from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Czlonkostwo, Dostep, Firma, Produkt, Zaproszenie


class DostepInline(admin.TabularInline):
    model = Dostep
    extra = 0


class CzlonkostwoInline(admin.TabularInline):
    model = Czlonkostwo
    extra = 0


@admin.register(Firma)
class FirmaAdmin(SimpleHistoryAdmin):
    list_display = ["nazwa", "aktywna", "utworzono"]
    search_fields = ["nazwa"]
    inlines = [CzlonkostwoInline]


@admin.register(Czlonkostwo)
class CzlonkostwoAdmin(SimpleHistoryAdmin):
    list_display = ["user", "firma", "wlasciciel", "aktywne"]
    list_filter = ["firma", "wlasciciel", "aktywne"]
    inlines = [DostepInline]


@admin.register(Produkt)
class ProduktAdmin(SimpleHistoryAdmin):
    list_display = ["kod", "nazwa", "adres", "klient"]


@admin.register(Zaproszenie)
class ZaproszenieAdmin(SimpleHistoryAdmin):
    list_display = ["email", "firma", "wazne_do", "uzyte"]
    exclude = ["token_hash"]
