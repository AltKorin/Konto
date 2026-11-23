"""produkty.json → baza (nazwy, adresy, role). Idempotentne — uruchamiane przy każdym starcie kontenera."""
from django.core.management.base import BaseCommand

from konto.uslugi import wczytaj_produkty


class Command(BaseCommand):
    help = "Wczytaj rejestr produktów z produkty.json."

    def handle(self, *args, **opts):
        for kod, nowy in wczytaj_produkty():
            self.stdout.write(f"{kod}: {'dodany' if nowy else 'aktualny'}")
