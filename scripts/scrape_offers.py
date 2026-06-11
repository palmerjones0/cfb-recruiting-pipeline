"""
scrape_offers.py — Scrape 247Sports offer pages for 2026–2028 using Playwright.

Prerequisites:
    python -m playwright install chromium

Usage:
    python scripts/scrape_offers.py
    python scripts/scrape_offers.py --schools "Alabama,Georgia"   # limit to specific schools
    python scripts/scrape_offers.py --years 2026 2027             # limit years
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).parent))
from school_slugs import make_slug

RAW_DIR = Path("data/raw")
OFFERS_DIR = Path("data/offers_raw")
OFFERS_DIR.mkdir(parents=True, exist_ok=True)

SCRAPE_YEARS = [2026, 2027, 2028]
CACHE_TTL_DAYS = 7
BASE_URL = "https://247sports.com/college/{slug}/season/{year}-football/offers/"


def is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return datetime.now(tz=timezone.utc) - mtime < timedelta(days=CACHE_TTL_DAYS)


def load_schools(filter_names=None) -> list:
    schools_path = RAW_DIR / "schools_raw.json"
    if not schools_path.exists():
        print("ERROR: data/raw/schools_raw.json not found. Run fetch_recruits.py first.")
        sys.exit(1)

    schools = json.loads(schools_path.read_text())
    result = []
    for s in schools:
        name = s.get("school") or s.get("name", "")
        slug = make_slug(name)
        if filter_names and name not in filter_names:
            continue
        result.append({"name": name, "slug_247": slug})
    return result


async def click_load_more(page) -> None:
    """Click all 'Load More' links until none remain (per-position-group on 247Sports)."""
    max_clicks = 50
    for _ in range(max_clicks):
        try:
            btns = await page.query_selector_all("a:has-text('Load More')")
            visible = []
            for btn in btns:
                if await btn.is_visible():
                    visible.append(btn)
            if not visible:
                break
            await visible[0].click()
            await page.wait_for_timeout(1500)
        except PlaywrightTimeout:
            break
        except Exception:
            break


async def parse_offer_page(page) -> list:
    """Extract offer records from a loaded 247Sports offer page."""
    recruits = []
    # Each data row is .ri-page__list-item containing a.ri-page__name-link
    items = await page.query_selector_all(".ri-page__list-item")
    for item in items:
        record = await extract_recruit_from_item(item)
        if record:
            recruits.append(record)
    return recruits


async def extract_recruit_from_item(item):
    """Extract a single recruit from a .ri-page__list-item element."""
    try:
        name_el = await item.query_selector("a.ri-page__name-link")
        if not name_el:
            return None
        name = (await name_el.inner_text()).strip()
        if not name:
            return None

        # Position
        pos_el = await item.query_selector(".position")
        position = (await pos_el.inner_text()).strip() if pos_el else ""

        # Stars — count yellow filled stars
        star_els = await item.query_selector_all(".icon-starsolid.yellow")
        stars = len(star_els)

        # Rating (composite score 0-100)
        score_el = await item.query_selector(".ri-page__star-and-score .score")
        rating_247 = None
        if score_el:
            score_text = (await score_el.inner_text()).strip()
            try:
                rating_247 = float(score_text)
            except ValueError:
                pass

        # City/state from .meta — text like "School Name (City, ST)"
        city, state = "", ""
        meta_el = await item.query_selector(".recruit .meta")
        if meta_el:
            meta_text = (await meta_el.inner_text()).strip()
            m = re.search(r"\(([^)]+)\)", meta_text)
            if m:
                loc = m.group(1).strip()
                parts = [p.strip() for p in loc.split(",")]
                city = parts[0] if parts else ""
                state = parts[-1] if len(parts) >= 2 else ""

        # Committed school — .status img[alt] is school name, absent if uncommitted
        status_img = await item.query_selector(".status img")
        committed_to = None
        if status_img:
            committed_to = await status_img.get_attribute("alt")

        return {
            "name": name,
            "position": position,
            "stars": stars,
            "rating_247": rating_247,
            "city": city,
            "state": state,
            "committed_to": committed_to,
        }

    except Exception:
        return None


async def scrape_school_year(
    browser, school_name: str, slug: str, year: int, errors: list
) -> None:
    cache_path = OFFERS_DIR / f"{slug}_{year}.json"
    if is_cache_fresh(cache_path):
        print(f"    {school_name} {year}: cached, skipping")
        return

    url = BASE_URL.format(slug=slug, year=year)
    print(f"    {school_name} {year}: {url}")

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        await click_load_more(page)
        recruits = await parse_offer_page(page)
        cache_path.write_text(json.dumps(recruits, indent=2))
        print(f"    {school_name} {year}: {len(recruits)} offers saved")
    except PlaywrightTimeout:
        print(f"    {school_name} {year}: TIMEOUT — skipping")
        errors.append(f"{school_name} {year}: timeout")
    except Exception as e:
        print(f"    {school_name} {year}: ERROR — {e}")
        errors.append(f"{school_name} {year}: {e}")
    finally:
        await context.close()


async def main(filter_schools=None, years=None):
    scrape_years = years or SCRAPE_YEARS
    schools = load_schools(filter_schools)
    print(f"Scraping {len(schools)} schools × {len(scrape_years)} years")

    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        for school in schools:
            for year in scrape_years:
                await scrape_school_year(
                    browser, school["name"], school["slug_247"], year, errors
                )
        await browser.close()

    if errors:
        print(f"\nFailed ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
    else:
        print("\nAll schools scraped successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schools", help="Comma-separated school names to limit scrape", default=None
    )
    parser.add_argument("--years", nargs="+", type=int, help="Years to scrape", default=None)
    args = parser.parse_args()

    filter_schools = [s.strip() for s in args.schools.split(",")] if args.schools else None
    asyncio.run(main(filter_schools=filter_schools, years=args.years))
