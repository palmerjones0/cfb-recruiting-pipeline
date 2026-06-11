"""
build_json.py — Build public/ output files from raw data.

Usage:
    python scripts/build_json.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from school_slugs import make_slug, NAME_247_TO_CFBD

# State centroids as fallback when a player isn't in CFBD yet
STATE_CENTROIDS = {
    "AL":(32.7794,-86.8287),"AK":(64.4459,-153.0),"AZ":(34.2744,-111.6602),
    "AR":(34.8938,-92.4426),"CA":(37.1841,-119.4696),"CO":(38.9972,-105.5478),
    "CT":(41.6219,-72.7273),"DE":(38.9896,-75.505),"FL":(28.6305,-82.4497),
    "GA":(32.6415,-83.4426),"HI":(20.2927,-156.3737),"ID":(44.3509,-114.6130),
    "IL":(40.0417,-89.1965),"IN":(39.8942,-86.2816),"IA":(42.0751,-93.4960),
    "KS":(38.4937,-98.3804),"KY":(37.5347,-85.3021),"LA":(31.0689,-91.9968),
    "ME":(45.3695,-69.2428),"MD":(39.0550,-76.7909),"MA":(42.2596,-71.8083),
    "MI":(44.3467,-85.4102),"MN":(46.2807,-94.3053),"MS":(32.7364,-89.6678),
    "MO":(38.3566,-92.4580),"MT":(47.0527,-109.6333),"NE":(41.5378,-99.7951),
    "NV":(39.3289,-116.6312),"NH":(43.6805,-71.5811),"NJ":(40.1907,-74.6728),
    "NM":(34.4071,-106.1126),"NY":(42.9538,-75.5268),"NC":(35.5557,-79.3877),
    "ND":(47.4501,-100.4659),"OH":(40.2862,-82.7937),"OK":(35.5889,-97.4943),
    "OR":(43.9336,-120.5583),"PA":(40.8781,-77.7996),"RI":(41.6762,-71.5562),
    "SC":(33.9169,-80.8964),"SD":(44.4443,-100.2263),"TN":(35.8580,-86.3505),
    "TX":(31.4757,-99.3312),"UT":(39.3210,-111.0937),"VT":(44.0687,-72.6658),
    "VA":(37.5215,-78.8537),"WA":(47.3826,-120.4472),"WV":(38.6409,-80.6227),
    "WI":(44.6243,-89.9941),"WY":(42.9957,-107.5512),"DC":(38.9101,-77.0147),
    "PR":(18.2208,-66.5901),
}

RAW_DIR = Path("data/raw")
OFFERS_DIR = Path("data/offers_raw")
PUBLIC_DIR = Path("public")
PUBLIC_OFFERS_DIR = PUBLIC_DIR / "offers"

PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_OFFERS_DIR.mkdir(parents=True, exist_ok=True)

RECRUIT_YEARS = range(2015, 2029)
OFFER_YEARS = [2026, 2027, 2028]

LOCATION_OVERRIDES = {
    "Northwestern": (42.0587, -87.6777),
    "Florida International": (25.7562, -80.3742),
}

US_COUNTRY_VALUES = {"", "USA", "US", None}


# ---------------------------------------------------------------------------
# Step 1 — Build schools.json
# ---------------------------------------------------------------------------

def build_schools() -> list:
    schools_path = RAW_DIR / "schools_raw.json"
    if not schools_path.exists():
        print("WARN: data/raw/schools_raw.json not found — skipping schools")
        return []

    raw = json.loads(schools_path.read_text())
    schools = []

    for s in raw:
        name = s.get("school") or s.get("name", "")
        if not name:
            continue

        abbrev = s.get("abbreviation", "")
        conference = s.get("conference", "")

        # Lat/lng — check location override first, then API fields
        if name in LOCATION_OVERRIDES:
            lat, lng = LOCATION_OVERRIDES[name]
        else:
            location = s.get("location") or {}
            lat = location.get("latitude") or s.get("latitude")
            lng = location.get("longitude") or s.get("longitude")

        schools.append({
            "id": name,
            "name": name,
            "abbreviation": abbrev,
            "conference": conference,
            "lat": lat,
            "lng": lng,
            "slug_247": make_slug(name),
        })

    schools.sort(key=lambda x: x["name"])
    (PUBLIC_DIR / "schools.json").write_text(json.dumps(schools, separators=(",", ":")))
    print(f"schools.json: {len(schools)} schools written")
    return schools


# ---------------------------------------------------------------------------
# Step 2 — Build players.json
# ---------------------------------------------------------------------------

def normalize_country(country) -> str:
    return (country or "").strip().upper()


def is_us_recruit(recruit: dict) -> bool:
    country = normalize_country(recruit.get("country"))
    return country in {"", "USA", "US"}


def get_latlon(recruit: dict) -> tuple:
    hometown = recruit.get("hometownInfo") or {}
    lat = hometown.get("latitude")
    lng = hometown.get("longitude")
    return lat, lng


def build_players(valid_school_ids: set) -> list:
    players = []
    year_counts = {}

    for year in RECRUIT_YEARS:
        path = RAW_DIR / f"recruits_{year}.json"
        if not path.exists():
            print(f"WARN: recruits_{year}.json not found — skipping {year}")
            continue

        raw = json.loads(path.read_text())
        count = 0

        for r in raw:
            if not is_us_recruit(r):
                continue

            lat, lng = get_latlon(r)
            if lat is None or lng is None:
                continue

            committed_to = r.get("committedTo") or None

            # 2015–2025: only include committed recruits with a valid school
            if year <= 2025:
                if not committed_to or committed_to not in valid_school_ids:
                    continue

            players.append({
                "name": r.get("name", ""),
                "school_id": committed_to,
                "position": r.get("position", ""),
                "stars": r.get("stars"),
                "rating": r.get("rating"),
                "year": year,
                "committed_to": committed_to,
                "lat": lat,
                "lng": lng,
                "hometown_city": r.get("city", ""),
                "hometown_state": r.get("stateProvince", ""),
            })
            count += 1

        year_counts[year] = count

    (PUBLIC_DIR / "players.json").write_text(json.dumps(players, separators=(",", ":")))
    total = sum(year_counts.values())
    print(f"players.json: {total} recruits written")
    for yr, ct in sorted(year_counts.items()):
        print(f"  {yr}: {ct}")

    return players


# ---------------------------------------------------------------------------
# Step 3 — Build per-school offer files (public/offers/{slug}.json)
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def build_player_lookup(players: list[dict]) -> dict[tuple, dict]:
    """Return {(normalized_name, year): player_record} for 2026+ players."""
    lookup = {}
    for p in players:
        if p["year"] >= 2026:
            key = (normalize_name(p["name"]), p["year"])
            lookup[key] = p
    return lookup


def load_offer_files() -> dict:
    """Return {slug: {year: [raw_offer_records]}}."""
    result: dict[str, dict[int, list[dict]]] = {}

    for year in OFFER_YEARS:
        for path in OFFERS_DIR.glob(f"*_{year}.json"):
            slug = path.stem[: -len(f"_{year}")]
            records = json.loads(path.read_text())
            if not isinstance(records, list):
                continue
            result.setdefault(slug, {}).setdefault(year, [])
            result[slug][year] = records

    return result


def build_offer_files(schools: list, players: list) -> tuple:
    """
    Write public/offers/{slug}.json for each school.
    Returns (files_written, player_offers_map, pipeline_player_records).
    player_offers_map: {"name|year": ["School1", ...]}
    pipeline_player_records: deduplicated list of offer records (one per unique name+year)
    """
    player_lookup = build_player_lookup(players)
    slug_to_name = {s["slug_247"]: s["name"] for s in schools}

    offer_data = load_offer_files()
    if not offer_data:
        print("WARN: no offer files found in data/offers_raw/ — skipping offer output")
        return 0, {}, []

    player_offers = {}
    pipeline_seen = {}  # (normalized_name, year) -> offer_rec (first occurrence wins)
    files_written = 0

    for slug, years_data in offer_data.items():
        school_name = slug_to_name.get(slug, slug)
        output = {}

        for year, records in sorted(years_data.items()):
            year_offers = []
            for rec in records:
                raw_name = rec.get("name", "")
                key = (normalize_name(raw_name), year)
                cfbd = player_lookup.get(key)

                # Get lat/lng from CFBD; fall back to state centroid if not in CFBD
                if cfbd is not None:
                    lat, lng = cfbd["lat"], cfbd["lng"]
                    hometown_city = cfbd.get("hometown_city", "")
                    hometown_state = cfbd.get("hometown_state", "")
                    stars = cfbd.get("stars")
                else:
                    state_abbrev = rec.get("state", "")
                    centroid = STATE_CENTROIDS.get(state_abbrev)
                    if not centroid:
                        continue  # Unknown state, skip
                    lat, lng = centroid
                    hometown_city = rec.get("city", "")
                    hometown_state = state_abbrev
                    stars = None  # No CFBD rating available

                # Normalize 247Sports school name to CFBD name for consistent comparison
                committed_247 = rec.get("committed_to")
                committed_cfbd = NAME_247_TO_CFBD.get(committed_247, committed_247) if committed_247 else None

                offer_rec = {
                    "name": raw_name,
                    "year": year,
                    "position": rec.get("position", ""),
                    "stars": stars,
                    "rating_247": rec.get("rating_247"),
                    "committed_to": committed_cfbd,
                    "lat": lat,
                    "lng": lng,
                    "hometown_city": hometown_city,
                    "hometown_state": hometown_state,
                }
                year_offers.append(offer_rec)

                # Deduplicate for pipeline_players.json (first school encountered wins)
                if key not in pipeline_seen:
                    pipeline_seen[key] = offer_rec

                # Accumulate player_offers map
                po_key = f"{raw_name}|{year}"
                player_offers.setdefault(po_key, [])
                if school_name not in player_offers[po_key]:
                    player_offers[po_key].append(school_name)

            output[str(year)] = year_offers

        out_path = PUBLIC_OFFERS_DIR / f"{slug}.json"
        out_path.write_text(json.dumps(output, separators=(",", ":")))
        files_written += 1

    print(f"offers/{{slug}}.json: {files_written} files written")
    pipeline_records = sorted(pipeline_seen.values(), key=lambda p: (p["year"], -(p["stars"] or 0)))
    return files_written, player_offers, pipeline_records


# ---------------------------------------------------------------------------
# Step 4 — Build player_offers.json + pipeline_players.json
# ---------------------------------------------------------------------------

def build_player_offers(player_offers: dict) -> None:
    out_path = PUBLIC_DIR / "player_offers.json"
    out_path.write_text(json.dumps(player_offers, separators=(",", ":")))
    print(f"player_offers.json: {len(player_offers)} entries written")


def build_pipeline_players(pipeline_records: list) -> None:
    out_path = PUBLIC_DIR / "pipeline_players.json"
    out_path.write_text(json.dumps(pipeline_records, separators=(",", ":")))
    print(f"pipeline_players.json: {len(pipeline_records)} unique players written")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Step 1: schools.json ===")
    schools = build_schools()
    valid_school_ids = {s["id"] for s in schools}

    print("\n=== Step 2: players.json ===")
    players = build_players(valid_school_ids)

    print("\n=== Step 3: offers/{slug}.json ===")
    files_written, player_offers, pipeline_records = build_offer_files(schools, players)

    print("\n=== Step 4: player_offers.json + pipeline_players.json ===")
    build_player_offers(player_offers)
    build_pipeline_players(pipeline_records)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
