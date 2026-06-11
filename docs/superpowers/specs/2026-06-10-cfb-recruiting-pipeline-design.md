# CFB Recruiting Pipeline — Design Spec
**Date:** 2026-06-10
**Status:** Approved
**Repo:** `cfb-recruiting-pipeline` (new standalone GitHub Pages site)

---

## Overview

An interactive US map with two modes:

- **School Mode** (default): Select any FBS program → see arcs from recruit hometowns to the school. Three arc types: solid (committed), dashed (offered + uncommitted pipeline target), hairline gray (offered + committed elsewhere).
- **Player Mode**: Tap a US state → see list of uncommitted recruits from that state → tap a player → see arcs to every school that has offered them.

Year filter applies to both modes. Pipeline arcs (dashed/hairline) only appear for 2026+ classes; pre-2026 shows committed arcs only.

**May replace cfb-recruiting-viz:** If this tool proves complete enough, it could replace the existing origins map entirely. Build with that in mind.

---

## Data Layer

### Sources by Class Year

| Class | Source | Content |
|-------|--------|---------|
| 2015–2025 | CFBD API (historical) | Committed recruits only |
| 2026–2028 | CFBD API (daily 4:15am ET) | Committed + uncommitted recruits |
| 2026–2028 | 247Sports (weekly, Sunday 3am ET) | Per-school full offer lists |

### Output Files (`public/`)

| File | Contents |
|------|---------|
| `schools.json` | All FBS schools: `{id, name, abbreviation, conference, lat, lng, slug_247}` |
| `players.json` | All recruits 2015–2028: `{name, school_id, position, stars, rating, year, committed_to, lat, lng, hometown_city, hometown_state}` — `committed_to` is null for uncommitted |
| `player_offers.json` | 2026+ only: `{"Name\|year": ["School1", "School2", ...]}` — loaded at startup |
| `offers/{slug}.json` | Per-school: `{2026: [{name, position, stars, rating_247, committed_to, lat, lng, hometown_city, hometown_state}], ...}` — lazy-loaded on school selection |
| `us-states.topojson` | US state boundaries |

### Update Schedule (Mac mini launchd)

- **Daily 4:15am ET**: `fetch_recruits.py` pulls 2026–2028 from CFBD → `build_json.py` rebuilds `players.json` → git push
- **Sunday 3am ET**: `scrape_offers.py` scrapes all ~130 FBS school offer pages via Playwright → `build_json.py` rebuilds offer files → git push
- Sunday also runs the daily step (CFBD pull + full rebuild)

---

## School Mode UX

Default view. Controls bar: title + school search + year dropdown + [School|Player] toggle + About.

**Arc types (2026+ classes only when a single year is selected):**

| Arc | Meaning | Style |
|-----|---------|-------|
| Solid colored | Committed to this school | Star colors, opacity 0.55, stroke 1.0 |
| Dashed colored | Offered + uncommitted | Same star colors, `stroke-dasharray: 5,4`, opacity 0.60, stroke 0.8 |
| Hairline gray | Offered + committed elsewhere | `#484f58`, opacity 0.20, stroke 0.4, `stroke-dasharray: 3,5` |

**When "All Years" is selected:** solid committed arcs only (no pipeline layer — too cluttered).
**When pre-2026 year selected:** solid committed arcs only.
**When 2026+ year selected:** all three arc types.

**School bar** (below controls, visible when school selected):
- School name
- Counts: `14 commits · 31 targets · 58 lost` (tappable → players panel)
- Players panel has three tabs: **Commits** | **Targets** | **Lost**

**Data flow on school selection:**
1. Draw solid arcs from `players.json` (committed_to === school.id && year matches)
2. If 2026+ single year: lazy-load `offers/{slug}.json`, draw dashed (committed_to null) + hairline (committed_to other school) arcs
3. Zoom to fit all arc endpoints

---

## Player Mode UX

Toggle via [School|Player] segmented control in controls bar. Year filter shows 2026–2028 only (default: 2026). School search hidden.

**Map state:**
- School dots dimmed (smaller radius, reduced opacity)
- State regions become clickable (pointer cursor, subtle hover fill)
- State fill intensity = density of uncommitted recruits in that state for selected year (computed client-side from `players.json`)

**Tap state → recruit panel:**
- Bottom panel slides up (same panel component as school mode)
- Title: `{State} · {N} uncommitted recruits ({Year})`
- List: star dot · name · position · ranking · high school — sorted by stars desc
- Tap any row → player arc view

**Player arc view:**
- Panel shrinks to a sticky header showing player name + stars + position + "← Back"
- Arcs animate from player's hometown dot to all offering schools
- Committed school arc: gold (`#d29922`), that school's dot highlighted with gold ring
- Other offering schools: blue (`#388bfd`), normal dots lit up
- Map zooms to fit hometown + all school dots
- Tap a school dot → tooltip shows school name + conference + "View school →" (switches to school mode for that school)

---

## Arc Rendering Details

`arcPath(sx, sy, tx, ty)` — same quadratic bezier helper as existing tool.

Arc draw-in animation: `stroke-dashoffset` tween, staggered delays (same as existing).

Three arc layers rendered in z-order: hairline (bottom) → dashed (middle) → solid (top).

Hometown dot radius: scaled by stars (larger = higher rated).

---

## 247Sports Slug Mapping

CFBD school names → 247Sports URL slugs. Auto-generation: lowercase + hyphens. Manual overrides for non-obvious cases (Ole Miss, UNLV, TCU, LSU, etc.). Maintained in `scripts/school_slugs.py`.

---

## Repo Structure

```
cfb-recruiting-pipeline/
├── .env.example
├── .gitignore
├── requirements.txt
├── scripts/
│   ├── school_slugs.py        # CFBD name → 247Sports slug mapping
│   ├── fetch_recruits.py      # CFBD API pull
│   ├── scrape_offers.py       # 247Sports Playwright scraper
│   ├── build_json.py          # Merge → public/ output files
│   └── sync.sh                # Orchestrator (daily/weekly)
├── data/
│   ├── raw/                   # gitignored CFBD cache
│   └── offers_raw/            # gitignored 247Sports cache
├── public/
│   ├── index.html
│   ├── players.json
│   ├── schools.json
│   ├── player_offers.json
│   ├── offers/                # per-school offer files
│   └── us-states.topojson
├── docs/superpowers/specs/    # this file
└── launchd/
    └── com.donna.cfb-pipeline-daily.plist
    └── com.donna.cfb-pipeline-weekly.plist
```
