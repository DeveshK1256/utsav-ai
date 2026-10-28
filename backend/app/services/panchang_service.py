"""
Panchang and Muhurat Astronomical Engine.
DEC-027: Deterministic ephemeris calculations using PyEphem and Lahiri (Chitrapaksha) Ayanamsha.
Zero LLM mathematical approximation.
"""

import math
from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any, ClassVar

import ephem


class PanchangProvider(ABC):
    """Abstract provider interface for astronomical panchang and muhurat calculations."""

    @abstractmethod
    def calculate_panchang(
        self,
        event_date: date,
        latitude: float,
        longitude: float,
        elevation_meters: float = 0.0,
    ) -> dict[str, Any]:
        """
        Calculates sunrise, sunset, Rahu Kaal, Abhijit Muhurat, Tithi, Nakshatra, and returns
        the mandatory priest verification disclaimer.
        """


class EphemPanchangProvider(PanchangProvider):
    """
    Deterministic PyEphem implementation of Panchang & Auspicious Muhurats.
    Uses VSOP87 planetary theory, topocentric apparent horizon (90° 50' zenith),
    and Chitrapaksha (Lahiri) Ayanamsha for sidereal Vedic lunar positions.
    """

    TITHI_NAMES: ClassVar[list[str]] = [
        "Shukla Pratipada",
        "Shukla Dwitiya",
        "Shukla Tritiya",
        "Shukla Chaturthi",
        "Shukla Panchami",
        "Shukla Shashthi",
        "Shukla Saptami",
        "Shukla Ashtami",
        "Shukla Navami",
        "Shukla Dashami",
        "Shukla Ekadashi",
        "Shukla Dwadashi",
        "Shukla Trayodashi",
        "Shukla Chaturdashi",
        "Purnima",
        "Krishna Pratipada",
        "Krishna Dwitiya",
        "Krishna Tritiya",
        "Krishna Chaturthi",
        "Krishna Panchami",
        "Krishna Shashthi",
        "Krishna Saptami",
        "Krishna Ashtami",
        "Krishna Navami",
        "Krishna Dashami",
        "Krishna Ekadashi",
        "Krishna Dwadashi",
        "Krishna Trayodashi",
        "Krishna Chaturdashi",
        "Amavasya",
    ]

    NAKSHATRA_NAMES: ClassVar[list[str]] = [
        "Ashwini",
        "Bharani",
        "Krittika",
        "Rohini",
        "Mrigashirsha",
        "Ardra",
        "Punarvasu",
        "Pushya",
        "Ashlesha",
        "Magha",
        "Purva Phalguni",
        "Uttara Phalguni",
        "Hasta",
        "Chitra",
        "Swati",
        "Vishakha",
        "Anuradha",
        "Jyeshtha",
        "Mula",
        "Purva Ashadha",
        "Uttara Ashadha",
        "Shravana",
        "Dhanishta",
        "Shatabhisha",
        "Purva Bhadrapada",
        "Uttara Bhadrapada",
        "Revati",
    ]

    # Traditional 1-based octile mapping for Rahu Kaalam
    # Monday: 2nd, Tuesday: 7th, Wednesday: 5th, Thursday: 6th
    # Friday: 4th, Saturday: 3rd, Sunday: 8th
    RAHU_OCTILES: ClassVar[dict[int, int]] = {
        0: 2,  # Monday
        1: 7,  # Tuesday
        2: 5,  # Wednesday
        3: 6,  # Thursday
        4: 4,  # Friday
        5: 3,  # Saturday
        6: 8,  # Sunday
    }

    DISCLAIMER_COPY = (
        "Calculated using Drik astronomical formulas with Chitrapaksha (Lahiri) Ayanamsha "
        "for your specific venue location. Regional traditions, family Kul-Purohits, and local "
        "panchang almanacs often vary by 10–20 minutes due to differing horizon and "
        "refraction models. ALWAYS confirm your final wedding pheras and vidhi muhurat "
        "with your family priest / Panditji."
    )

    @staticmethod
    def get_lahiri_ayanamsha(jd: float) -> float:
        """
        Calculates Chitrapaksha (Lahiri) Ayanamsha in degrees for a given Julian Date.
        J2000.0 (JD 2451545.0) baseline: 23° 51' 25.53" = 23.8570916667°.
        Annual precession rate: 50.290966" / year.
        """
        t_centuries = (jd - 2451545.0) / 36525.0
        ayan = 23.8570916667 + (5029.0966 * t_centuries + 1.112 * (t_centuries**2)) / 3600.0
        return ayan

    def calculate_panchang(
        self,
        event_date: date,
        latitude: float,
        longitude: float,
        elevation_meters: float = 0.0,
    ) -> dict[str, Any]:
        """Calculates precise panchang parameters for a given date and geographic location."""
        obs = ephem.Observer()
        obs.lat = str(latitude)
        obs.lon = str(longitude)
        obs.elevation = float(elevation_meters)
        obs.pressure = 1010.0
        obs.temp = 25.0

        # Anchor observer at local midnight IST (UTC + 5:30) = 18:30 UTC of previous day
        dt_local_midnight = datetime.combine(event_date, time(0, 0, 0))
        dt_utc_start = dt_local_midnight - timedelta(hours=5, minutes=30)
        obs.date = ephem.Date(dt_utc_start)

        sun = ephem.Sun()
        moon = ephem.Moon()

        # Astronomical topocentric apparent rising and setting
        sunrise_ephem = obs.next_rising(sun)
        obs.date = sunrise_ephem
        sunset_ephem = obs.next_setting(sun)

        sunrise_utc = sunrise_ephem.datetime().replace(tzinfo=UTC)
        sunset_utc = sunset_ephem.datetime().replace(tzinfo=UTC)

        ist = timezone(timedelta(hours=5, minutes=30))
        sunrise_ist = sunrise_utc.astimezone(ist)
        sunset_ist = sunset_utc.astimezone(ist)

        daylight_sec = (sunset_ist - sunrise_ist).total_seconds()
        octile_duration = daylight_sec / 8.0

        weekday = sunrise_ist.weekday()
        rahu_octile = self.RAHU_OCTILES[weekday]
        rahu_start = sunrise_ist + timedelta(seconds=(rahu_octile - 1) * octile_duration)
        rahu_end = sunrise_ist + timedelta(seconds=rahu_octile * octile_duration)

        # Abhijit Muhurat: 8th of 15 equal daytime muhurats (duration = daylight / 15)
        muhurat_len = daylight_sec / 15.0
        abhijit_start = sunrise_ist + timedelta(seconds=7 * muhurat_len)
        abhijit_end = sunrise_ist + timedelta(seconds=8 * muhurat_len)

        # Tithi and Nakshatra at local sunrise (Udaya Tithi rule)
        obs.date = sunrise_ephem
        sun.compute(obs)
        moon.compute(obs)

        sun_ecl = ephem.Ecliptic(sun)
        moon_ecl = ephem.Ecliptic(moon)

        sun_lon_deg = math.degrees(sun_ecl.lon) % 360.0
        moon_lon_deg = math.degrees(moon_ecl.lon) % 360.0

        # Tithi: relative elongation between Moon and Sun (12° per Tithi)
        elongation = (moon_lon_deg - sun_lon_deg) % 360.0
        tithi_idx = int(elongation / 12.0)
        tithi_progress = (elongation % 12.0) / 12.0
        paksha = "Shukla" if tithi_idx < 15 else "Krishna"

        # Nakshatra: Nirayana (sidereal) Moon longitude using Lahiri Ayanamsha
        # (13° 20' per Nakshatra)
        jd = ephem.julian_date(sunrise_ephem)
        ayanamsha = self.get_lahiri_ayanamsha(jd)
        sidereal_moon_lon = (moon_lon_deg - ayanamsha) % 360.0
        nakshatra_idx = int(sidereal_moon_lon / (360.0 / 27.0))
        nakshatra_progress = (sidereal_moon_lon % (360.0 / 27.0)) / (360.0 / 27.0)

        # Abhijit cautionary note for Wednesdays (Budhavara)
        abhijit_applicable = (
            weekday != 2
        )  # Wednesday has traditional taboo due to Rahu overlap / mutual affliction

        return {
            "date": event_date.isoformat(),
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_meters": elevation_meters,
            },
            "sunrise": sunrise_ist.strftime("%H:%M:%S"),
            "sunset": sunset_ist.strftime("%H:%M:%S"),
            "daylight_duration_seconds": int(daylight_sec),
            "daylight_formatted": str(timedelta(seconds=int(daylight_sec))),
            "rahu_kaal": {
                "start": rahu_start.strftime("%H:%M:%S"),
                "end": rahu_end.strftime("%H:%M:%S"),
                "octile_index": rahu_octile,
                "is_inauspicious": True,
            },
            "abhijit_muhurat": {
                "start": abhijit_start.strftime("%H:%M:%S"),
                "end": abhijit_end.strftime("%H:%M:%S"),
                "is_auspicious": abhijit_applicable,
                "caution": "Traditional calendars advise alternative muhurats on Wednesdays"
                if not abhijit_applicable
                else None,
            },
            "tithi": {
                "name": self.TITHI_NAMES[tithi_idx],
                "index": tithi_idx + 1,
                "paksha": paksha,
                "percent_elapsed": round(tithi_progress * 100.0, 1),
            },
            "nakshatra": {
                "name": self.NAKSHATRA_NAMES[nakshatra_idx],
                "index": nakshatra_idx + 1,
                "percent_elapsed": round(nakshatra_progress * 100.0, 1),
            },
            "ayanamsha": {
                "system": "Chitrapaksha (Lahiri)",
                "degrees": round(ayanamsha, 4),
            },
            "priest_disclaimer": self.DISCLAIMER_COPY,
        }


# Singleton instance
default_panchang_provider = EphemPanchangProvider()
