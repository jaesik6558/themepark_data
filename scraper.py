import csv
import datetime as dt
import os
import zoneinfo

import requests

PARKS = {
    125: {"name": "Everland", "lat": 37.2947, "lon": 127.2029},
    333: {"name": "Lotte World", "lat": 37.5111, "lon": 127.0980},
}

KST = zoneinfo.ZoneInfo("Asia/Seoul")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FIELDS = [
    "timestamp_kst", "park_id", "park_name", "land_name",
    "ride_id", "ride_name", "is_open", "wait_time_min",
    "temperature_c", "precipitation_mm", "weather_code",
    "humidity_pct", "wind_speed_kmh",
]


def fetch_queue_times(park_id):
    url = f"https://queue-times.com/parks/{park_id}/queue_times.json"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,precipitation,weather_code,relative_humidity_2m,wind_speed_10m"
        "&timezone=Asia%2FSeoul"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json().get("current", {})


def iter_rides(payload):
    for land in payload.get("lands", []):
        land_name = land.get("name")
        for ride in land.get("rides", []):
            yield land_name, ride
    for ride in payload.get("rides", []):
        yield None, ride


def main():
    now = dt.datetime.now(tz=KST)
    timestamp = now.isoformat()
    month_key = now.strftime("%Y-%m")
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"wait_times_{month_key}.csv")
    write_header = not os.path.exists(out_path)

    rows = []
    for park_id, meta in PARKS.items():
        try:
            payload = fetch_queue_times(park_id)
        except requests.RequestException as exc:
            print(f"[warn] failed to fetch park {park_id}: {exc}")
            continue

        try:
            weather = fetch_weather(meta["lat"], meta["lon"])
        except requests.RequestException as exc:
            print(f"[warn] failed to fetch weather for park {park_id}: {exc}")
            weather = {}

        for land_name, ride in iter_rides(payload):
            rows.append({
                "timestamp_kst": timestamp,
                "park_id": park_id,
                "park_name": meta["name"],
                "land_name": land_name,
                "ride_id": ride.get("id"),
                "ride_name": ride.get("name"),
                "is_open": ride.get("is_open"),
                "wait_time_min": ride.get("wait_time"),
                "temperature_c": weather.get("temperature_2m"),
                "precipitation_mm": weather.get("precipitation"),
                "weather_code": weather.get("weather_code"),
                "humidity_pct": weather.get("relative_humidity_2m"),
                "wind_speed_kmh": weather.get("wind_speed_10m"),
            })

    if not rows:
        print("[warn] no rows collected this run")
        return

    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    print(f"[ok] appended {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
