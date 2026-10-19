"""Building America interior lighting profile (OpenStudio-HPXML `schedules.rb` 700-813).

Monthly 24-hour profiles built from a morning curve, a daytime curve and an
evening peak tied to the month's sunset time. Sunset comes from a simple solar
equation; at latitudes of 51.49 degrees and above upstream uses a fixed table.
The `offset` of one hour for April-October is part of the upstream equation,
not a daylight-saving conversion.
"""
import math

from ..errors import GeneratorError
from .seasons import season_month

HIGH_LATITUDE_SUNSET = (16.22214058, 17.08642353, 17.98324493, 19.83547864, 20.65149672, 21.20662992,
                        21.12124777, 20.37458274, 19.25834757, 18.08155615, 16.14359164, 15.75571306)
MORNING = (0.060, 0.040, 0.035, 0.025, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020)
LATE_PEAK_HOUR = 20.1501965859073
LATE_STD = 2.36567663279954
EVENING_SHIFT = 2.45016230615269


def sunset_hours(latitude: float, longitude: float, utc_offset: float) -> list:
    if latitude >= 51.49:
        return list(HIGH_LATITUDE_SUNSET)
    radians = math.pi / 180
    sunset = []
    for month in range(1, 13):
        julian = month * 30 - 15
        declination = 23.45 * math.sin(0.9863 * (284 + julian) * 0.01745329)
        b = (julian - 1) * 0.9863
        equation_of_time = 0.01667 * (0.01719 + 0.42815 * math.cos(radians * b) - 7.35205 * math.sin(radians * b)
                                      - 3.34976 * math.cos(radians * 2 * b) - 9.37199 * math.sin(radians * 2 * b))
        try:
            hour_angle = math.acos(-math.tan(radians * latitude) * math.tan(radians * declination)) / radians
        except ValueError as error:
            raise GeneratorError("source_undefined", "/inputs/latitude",
                                 "The upstream sunset equation is undefined here") from error
        offset = 1 if 4 <= season_month(month, latitude) <= 10 else 0
        sunset.append(offset + 12.0 + hour_angle / 15.0 - equation_of_time - (-utc_offset * 15 + longitude) / 15)
    return sunset


def _late(hour: float) -> float:
    return 0.04 + 1.1372291802273 * math.exp(-(hour - LATE_PEAK_HOUR) ** 2 / (2 * LATE_STD ** 2)) / (
        LATE_STD * math.sqrt(2 * math.pi))


def _month_profile(month: int, sunset: float, seasonal: float) -> list:
    half = list(MORNING) + [0.0] * 38
    for index in range(9, 18):
        hour = (index + 1.0) * 0.5
        half[index] = (half[8] - 0.15 / (2 * math.pi) * math.sin(2 * math.pi * (hour - 4.5) / 3.5)
                       + 0.15 / 3.5 * (hour - 4.5)) * seasonal
    for index in range(17, 30):
        hour = (index + 1.0) * 0.5
        half[index] = (half[16] - (-0.02 / (2 * math.pi)) * math.sin(2 * math.pi * (hour - 8.5) / 5.5)
                       + (-0.02 / 5.5) * (hour - 8.5)) * seasonal
    std = 25.5 / (abs(6.5 - month) + 20.0) * 1.58679810983444

    def evening(hour):
        return 0.929707907917098 * math.exp(-(hour - (sunset + EVENING_SHIFT)) ** 2 / (2 * std ** 2)) / (
            std * math.sqrt(2 * math.pi))

    for index in range(29, 46):
        half[index] = half[28] + evening((index + 1.0) * 0.5)
    for index in range(45, 47):
        hour = (index + 1.0) * 0.5
        a = half[44] + evening(hour)
        b = _late(hour)
        half[index] = min(a, b) if LATE_PEAK_HOUR < sunset + EVENING_SHIFT else max(a, b)
    for index in range(46, 48):
        half[index] = _late((index + 1) * 0.5)
    return [half[h * 2] + half[h * 2 + 1] for h in range(24)]


def monthly_profiles(latitude: float, longitude: float, utc_offset: float, seasonal: list) -> list:
    """Twelve 24-hour profiles, normalised to the annual peak.

    `seasonal` must already follow the hemisphere (seasons.for_hemisphere); the
    evening-width month term uses the season month.
    """
    sunsets = sunset_hours(latitude, longitude, utc_offset)
    profiles = [_month_profile(season_month(m, latitude), sunsets[m - 1], seasonal[m - 1]) for m in range(1, 13)]
    peak = max(max(p) for p in profiles)
    return [[v / peak for v in p] for p in profiles]
