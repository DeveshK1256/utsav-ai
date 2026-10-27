"""
Panchang Astronomical Verification Suite — 3 Golden-Date Ground Truth Tests.
DEC-027: Deterministic ephemeris calculations using PyEphem and Lahiri (Chitrapaksha) Ayanamsha.

Astronomical Citations:
1. Positional Astronomy Centre (India Meteorological Department, Govt. of India),
   The Indian Astronomical Ephemeris (published annually).
2. Rashtriya Panchang (National Calendar of India), Astronomical Ephemeris Division, Kolkata.
3. Jiwaji Observatory (Vedh Shala), Ujjain (Prime Meridian of ancient Hindu astronomy).
"""

from datetime import date
import pytest
from backend.app.services.panchang_service import default_panchang_provider


def test_golden_date_1_varanasi_devutthana_ekadashi():
    """
    Golden Date 1: Devutthana Ekadashi (Auspicious Wedding Season Inauguration).
    Date: 2024-11-12
    Location: Varanasi, Uttar Pradesh (25.3176° N, 82.9739° E, 80m elev)
    Astronomical Ground Truth Citation:
      - Indian Astronomical Ephemeris 2024, Positional Astronomy Centre, Kolkata.
      - Drik Panchang Varanasi Ephemeris 2024.
      - Tithi: Shukla Ekadashi (11th waxing lunar day, Sun-Moon elongation 120°–132°).
      - Nakshatra: Purva Bhadrapada (25th Vedic asterism).
      - Rahu Kaal: Tuesday 7th octile.
    """
    res = default_panchang_provider.calculate_panchang(
        event_date=date(2024, 11, 12),
        latitude=25.3176,
        longitude=82.9739,
        elevation_meters=80.0
    )

    assert res["date"] == "2024-11-12"
    assert res["tithi"]["name"] == "Shukla Ekadashi"
    assert res["tithi"]["paksha"] == "Shukla"
    assert res["nakshatra"]["name"] == "Purva Bhadrapada"
    assert res["rahu_kaal"]["octile_index"] == 7
    assert res["rahu_kaal"]["is_inauspicious"] is True
    assert res["sunrise"].startswith("06:13")
    assert res["sunset"].startswith("17:11")
    assert "priest" in res["priest_disclaimer"].lower()


def test_golden_date_2_ujjain_makar_sankranti():
    """
    Golden Date 2: Makar Sankranti / Solar Ingress into Capricorn (Uttarayan).
    Date: 2025-01-14
    Location: Ujjain, Madhya Pradesh (23.1765° N, 75.7885° E, 492m elev)
    Astronomical Ground Truth Citation:
      - Rashtriya Panchang 2025 (Govt. of India), Ujjain Vedh Shala standard.
      - Jiwaji Observatory Astronomical Tables.
      - Tithi: Krishna Pratipada (1st waning lunar day).
      - Nakshatra: Punarvasu (7th Vedic asterism).
      - Rahu Kaal: Tuesday 7th octile.
    """
    res = default_panchang_provider.calculate_panchang(
        event_date=date(2025, 1, 14),
        latitude=23.1765,
        longitude=75.7885,
        elevation_meters=492.0
    )

    assert res["date"] == "2025-01-14"
    assert res["tithi"]["name"] == "Krishna Pratipada"
    assert res["tithi"]["paksha"] == "Krishna"
    assert res["nakshatra"]["name"] == "Punarvasu"
    assert res["rahu_kaal"]["octile_index"] == 7
    assert res["rahu_kaal"]["is_inauspicious"] is True
    assert res["sunrise"].startswith("07:10")
    assert res["sunset"].startswith("18:01")
    assert res["abhijit_muhurat"]["is_auspicious"] is True


def test_golden_date_3_pune_gudi_padwa():
    """
    Golden Date 3: Chaitra Shukla Pratipada / Gudi Padwa (Vedic New Year).
    Date: 2025-03-30
    Location: Pune, Maharashtra (18.5204° N, 73.8567° E, 560m elev)
    Astronomical Ground Truth Citation:
      - Tilak Panchang & Kalnirnay Astronomical Calendar 2025.
      - Positional Astronomy Centre, Kolkata (Chaitra New Year Ephemeris).
      - Tithi: Shukla Pratipada (1st waxing lunar day of Chaitra).
      - Nakshatra: Revati (27th Vedic asterism, completing the zodiacal cycle).
      - Rahu Kaal: Sunday 8th octile.
    """
    res = default_panchang_provider.calculate_panchang(
        event_date=date(2025, 3, 30),
        latitude=18.5204,
        longitude=73.8567,
        elevation_meters=560.0
    )

    assert res["date"] == "2025-03-30"
    assert res["tithi"]["name"] == "Shukla Pratipada"
    assert res["tithi"]["paksha"] == "Shukla"
    assert res["nakshatra"]["name"] == "Revati"
    assert res["rahu_kaal"]["octile_index"] == 8
    assert res["rahu_kaal"]["is_inauspicious"] is True
    assert res["sunrise"].startswith("06:30")
    assert res["sunset"].startswith("18:47")
    assert "panditji" in res["priest_disclaimer"].lower()
