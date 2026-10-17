"""Package TMY3 dry-bulb records for the 16 DOE Commercial Reference locations.

Source: data/raw/weather/usa-tmy3-epw.zip (locked TMY3 EPW archive) and the
location cases of NREL/TP-5500-46861 Table 2 (data/raw/doe-reference-locations,
SHA-256 locked; also docs/schedule-source-review.md). Table 2 names TMY2 weather
locations; this binds each to a TMY3 file:
- where the TMY3 set has one station for the named location, that station;
- otherwise the location's primary airport station, the one TMY2 used
  (Miami Intl, Houston Bush Intercontinental, Phoenix Sky Harbor,
  Seattle-Tacoma Intl, Chicago O'Hare as Table 2 states, Minneapolis-St. Paul Intl);
- 5B Boulder: the only Boulder-area TMY3 file (Boulder-Broomfield-Jefferson
  County AP), labelled as a proxy for the TMY2 Boulder station.

Writes atlas_schedules_v2/data/weather/<station>.json (dry-bulb, location, time
zone, as the existing station records) and data/weather/reference-locations.json.

Usage: python -m scripts.build_weather         (write)
       python -m scripts.build_weather --check (re-extract existing stations and compare)
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/weather/usa-tmy3-epw.zip"
TARGET = ROOT / "atlas_schedules_v2/data/weather"
LOCATIONS = [
    ("1A", "Miami, FL", "Miami, Florida", "USA_FL_Miami.Intl.AP.722020", "primary airport"),
    ("2A", "Houston, TX", "Houston, Texas", "USA_TX_Houston-Bush.Intercontinental.AP.722430", "primary airport"),
    ("2B", "Phoenix, AZ", "Phoenix, Arizona", "USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780", "primary airport"),
    ("3A", "Atlanta, GA", "Atlanta, Georgia", "USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190", "only station"),
    ("3B-CA", "Los Angeles, CA", "Los Angeles, California", "USA_CA_Los.Angeles.Intl.AP.722950", "only station"),
    ("3B-other", "Las Vegas, NV", "Las Vegas, Nevada", "USA_NV_Las.Vegas-McCarran.Intl.AP.723860", "only station"),
    ("3C", "San Francisco, CA", "San Francisco, California", "USA_CA_San.Francisco.Intl.AP.724940", "only station"),
    ("4A", "Baltimore, MD", "Baltimore, Maryland", "USA_MD_Baltimore-Washington.Intl.AP.724060", "only station"),
    ("4B", "Albuquerque, NM", "Albuquerque, New Mexico", "USA_NM_Albuquerque.Intl.AP.723650", "only station"),
    ("4C", "Seattle, WA", "Seattle, Washington", "USA_WA_Seattle-Tacoma.Intl.AP.727930", "primary airport"),
    ("5A", "Chicago, IL", "Chicago-O'Hare, Illinois", "USA_IL_Chicago-OHare.Intl.AP.725300", "named in Table 2"),
    ("5B", "Denver, CO", "Boulder, Colorado", "USA_CO_Boulder-Broomfield-Jefferson.County.AP.724699",
     "proxy: only Boulder-area TMY3 station"),
    ("6A", "Minneapolis, MN", "Minneapolis, Minnesota", "USA_MN_Minneapolis-St.Paul.Intl.AP.726580", "primary airport"),
    ("6B", "Helena, MT", "Helena, Montana", "USA_MT_Helena.Rgnl.AP.727720", "only station"),
    ("7", "Duluth, MN", "Duluth, Minnesota", "USA_MN_Duluth.Intl.AP.727450", "only station"),
    ("8", "Fairbanks, AK", "Fairbanks, Alaska", "USA_AK_Fairbanks.Intl.AP.702610", "only station"),
]


def station_record(archive: zipfile.ZipFile, station: str) -> dict:
    member = f"{station}_TMY3.epw"
    blob = archive.read(member)
    rows = list(csv.reader(io.StringIO(blob.decode("latin-1"))))
    header = rows[0]
    data = rows[8:8 + 8760]
    return {
        "schema_version": "1.0.0", "format": "epw", "station_header": header,
        "latitude": float(header[6]), "longitude": float(header[7]),
        "time_zone_utc_offset": float(header[8]), "elevation_m": float(header[9]),
        "first_source_row": 9, "source_column": 7,
        "drybulb_C": [float(row[6]) for row in data],
        "variant": "TMY3 station for a DOE Commercial Reference location",
        "provenance": {"source_id": "tmy3", "source_path": member, "source_sha256": hashlib.sha256(blob).hexdigest(),
                       "original_unit": "degC drybulb; decimal degrees; h UTC offset; m elevation",
                       "field_locator": "source_path#row=<1-based source line>/column=<1-based column>"},
    }


def main() -> None:
    with zipfile.ZipFile(ARCHIVE) as archive:
        if sys.argv[1:] == ["--check"]:
            for path in sorted(TARGET.glob("USA_*.json")):
                existing = json.loads(path.read_text(encoding="utf-8"))
                station = path.stem.removesuffix("_TMY3")
                rebuilt = station_record(archive, station)
                same = rebuilt["drybulb_C"] == existing["drybulb_C"] and all(
                    rebuilt[k] == existing[k] for k in ("latitude", "longitude", "time_zone_utc_offset"))
                print(station, "identical" if same else "DIFFERENT")
            return
        table = []
        for case, city, tmy2, station, rule in LOCATIONS:
            path = TARGET / f"{station}_TMY3.json"
            if not path.exists():
                path.write_text(json.dumps(station_record(archive, station), separators=(",", ":")) + "\n",
                                encoding="utf-8", newline="\n")
            record = json.loads(path.read_text(encoding="utf-8"))
            table.append({"climate_case": case, "representative_city": city, "tmy2_location": tmy2,
                          "weather_id": f"{station}_TMY3", "binding": rule, "state": station.split("_")[1],
                          "latitude": record["latitude"], "longitude": record["longitude"],
                          "utc_offset": record["time_zone_utc_offset"]})
        (TARGET / "reference-locations.json").write_text(
            json.dumps({"source": "NREL/TP-5500-46861 Table 2; TMY3 bindings per scripts/build_weather.py",
                        "locations": table}, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(len(table), "reference locations")


if __name__ == "__main__":
    main()
