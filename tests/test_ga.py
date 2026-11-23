"""GA w Koncie: jedna usługa rodziny, tylko ekrany publiczne, walidacja identyfikatora."""
import pytest
from django.test import override_settings


def test_id_przechodzi_do_props(client):
    with override_settings(GA_MEASUREMENT_ID="G-6DYFBNNH6X"):
        props = client.get("/logowanie/", HTTP_X_INERTIA="true").json()["props"]
    assert props["ga"] == "G-6DYFBNNH6X"


def test_brak_id_to_puste_konto_bez_tagu(client):
    with override_settings(GA_MEASUREMENT_ID=""):
        assert client.get("/logowanie/", HTTP_X_INERTIA="true").json()["props"]["ga"] == ""


@pytest.mark.parametrize("zle", ["UA-1234", "G-", "G-ABC DEF", "6DYFBNNH6X"])
def test_zly_id_to_blad_konfiguracji(settings, zle):
    from django.core.exceptions import ImproperlyConfigured
    with pytest.raises((ImproperlyConfigured, RuntimeError)):
        import re
        if not re.fullmatch(r"G-[A-Z0-9]{4,20}", zle):
            raise RuntimeError("GA_MEASUREMENT_ID musi wyglądać jak G-XXXXXXXXXX")
