"""
fetch_recruits.py — Pull recruiting and school data from the CFBD API.

Usage:
    python scripts/fetch_recruits.py
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["CFBD_API_KEY"]
BASE_URL = "https://api.collegefootballdata.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2015, 2029)
ALWAYS_REFRESH_FROM = 2026


def fetch_json(url: str, params: dict = None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_recruits():
    for year in YEARS:
        cache_path = RAW_DIR / f"recruits_{year}.json"

        if cache_path.exists() and year < ALWAYS_REFRESH_FROM:
            print(f"  {year}: cached, skipping")
            continue

        print(f"  {year}: fetching...")
        data = fetch_json(f"{BASE_URL}/recruiting/players", params={"year": year})
        cache_path.write_text(json.dumps(data, indent=2))
        print(f"  {year}: {len(data)} recruits saved")
        time.sleep(0.5)


def fetch_schools():
    schools_path = RAW_DIR / "schools_raw.json"
    print("Fetching FBS schools...")
    data = fetch_json(f"{BASE_URL}/teams/fbs")
    schools_path.write_text(json.dumps(data, indent=2))
    print(f"  {len(data)} schools saved")


if __name__ == "__main__":
    print("=== Fetching FBS schools ===")
    fetch_schools()

    print("\n=== Fetching recruits (2015–2028) ===")
    fetch_recruits()

    print("\nDone.")
