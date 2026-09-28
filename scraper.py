import csv
import datetime as dt
import os
import zoneinfo

import requests

PARKS = {
    125: {"name": "Everland"},
    333: {"name": "Lotte World"},
}

KST = zoneinfo.ZoneInfo("Asia/Seoul")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FIELDS = [
    "timestamp_kst", "park_id", "park_name", "land_name",
    "ride_id", "ride_name", "is_open", "wait_time_min",
]


def fetch_queue_times(park_id):
    url = f"https://queue-times.com/parks/{park_id}/queue_times.json"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


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
