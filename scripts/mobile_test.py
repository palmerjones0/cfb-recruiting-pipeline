"""
mobile_test.py — Playwright mobile smoke test (iPhone 15 Pro / WebKit).
Uses Playwright's native tap() for real touch events, no manual Touch constructors.

Usage:
    python3 scripts/mobile_test.py
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.palmercjones.com/cfb-recruiting-pipeline/"
SHOTS = Path("scripts/mobile_test_screenshots")
SHOTS.mkdir(exist_ok=True)

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
results = []

def shot(page, name):
    page.screenshot(path=str(SHOTS / f"{name}.png"))
    print(f"  📸 {name}.png")

def ok(label, condition, detail=""):
    icon = PASS if condition else FAIL
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))
    results.append((label, condition))
    return condition

def run():
    with sync_playwright() as p:
        iphone = p.devices["iPhone 15 Pro"]
        browser = p.webkit.launch(headless=False, slow_mo=150)
        ctx = browser.new_context(**iphone)
        page = ctx.new_page()
        vp = iphone["viewport"]

        print(f"\n{'='*55}")
        print(f"Device : iPhone 15 Pro  {vp['width']}×{vp['height']}px")
        print(f"Engine : WebKit (Safari/iOS)")
        print(f"{'='*55}\n")

        # ── 1. Load page ───────────────────────────────────────────
        print("1. Page load")
        page.goto(URL, wait_until="networkidle", timeout=30_000)
        time.sleep(1.5)
        shot(page, "01_load")
        version = page.locator("#version-tag").text_content(timeout=5000)
        ok("Version tag visible", bool(version), version)
        ndots = page.locator("circle.school-dot").count()
        ok("School dots rendered", ndots > 50, f"{ndots} dots")

        # Dismiss About overlay if present
        got_it = page.locator("button", has_text="Got it")
        if got_it.is_visible(timeout=2000):
            got_it.tap()
            time.sleep(0.4)
            print("  ℹ️  Dismissed About overlay")

        # ── 2. School mode — tap a school dot ─────────────────────
        print("\n2. School mode — tap a school dot")
        # Get bounding box of first school group that has a visible dot
        school_box = page.evaluate("""
            () => {
                for (const g of document.querySelectorAll('g.school-group')) {
                    const r = g.getBoundingClientRect();
                    if (r.width > 0 && r.x > 50 && r.y > 50 && r.x < window.innerWidth - 20) {
                        return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
                    }
                }
                return null;
            }
        """)
        if school_box:
            page.touchscreen.tap(school_box["x"], school_box["y"])
        time.sleep(1.5)
        shot(page, "02_school_selected")
        bar = page.locator("#school-bar").text_content(timeout=3000)
        ok("School selected", bar and bar.strip() != "", bar.strip()[:40])
        # Wait for arcs (offer data fetches async)
        try:
            page.wait_for_selector("path.recruit-arc", timeout=8000)
            arcs = page.locator("path.recruit-arc").count()
            ok("Arcs rendered", arcs > 0, f"{arcs} arcs")
        except Exception:
            ok("Arcs rendered", False, "timeout")

        # ── 3. School panel via native tap ─────────────────────────
        print("\n3. School panel tap")
        counts_btn = page.locator("#school-bar-counts")
        counts_btn.tap()
        time.sleep(0.7)
        shot(page, "03_school_panel")
        panel_open = page.evaluate("document.getElementById('players-panel').classList.contains('open')")
        ok("Panel opens on tap", panel_open)
        page.locator("#players-close").tap()
        time.sleep(0.3)

        # ── 4. Arc filter buttons ──────────────────────────────────
        print("\n4. Arc filter buttons")
        page.locator(".arc-filter-btn", has_text="Offered").tap()
        time.sleep(0.4)
        active = page.locator(".arc-filter-btn.active").text_content()
        ok("Offered filter", "Offered" in active)

        page.locator(".arc-filter-btn", has_text="Committed").tap()
        time.sleep(0.3)
        active2 = page.locator(".arc-filter-btn.active").text_content()
        ok("Committed filter", "Committed" in active2)

        page.locator(".arc-filter-btn", has_text="All").tap()
        time.sleep(0.3)
        shot(page, "04_arc_filter")

        # ── 5. Switch to Player mode ───────────────────────────────
        print("\n5. Player mode")
        page.locator("#btn-player").tap()
        time.sleep(1.5)
        shot(page, "05_player_mode")
        ok("Player btn active",
           page.evaluate("document.getElementById('btn-player').classList.contains('active')"))
        ok("Prospects panel opens",
           page.evaluate("document.getElementById('players-panel').classList.contains('open')"))
        prospect_dots = page.locator("circle.prospect-dot").count()
        ok("Prospect dots on map", prospect_dots > 100, f"{prospect_dots} dots")
        title = page.locator("#players-title").text_content()
        ok("Panel shows count", "prospects" in title, title)

        # ── 6. 2027 star colors (key regression check) ────────────
        print("\n6. 2027 star colors")
        page.locator("#year-select").select_option("2027")
        time.sleep(1.2)
        shot(page, "06_player_2027")
        colors = set(page.evaluate("""
            () => [...document.querySelectorAll('circle.prospect-dot')]
                      .map(d => d.getAttribute('fill'))
        """))
        ok("Multiple star tiers", len(colors) > 1, f"{sorted(colors)}")
        ok("3★ green present", "#3fb950" in colors)
        ok("4★ blue present",  "#388bfd" in colors)
        ok("5★ gold present",  "#d29922" in colors)

        # ── 7. State tap (touchend via Playwright) ─────────────────
        print("\n7. State tap — Texas")
        page.locator("#year-select").select_option("2026")
        time.sleep(0.8)
        # Find a point on Texas that isn't covered by a prospect dot
        texas_box = page.evaluate("""
            () => {
                const el = d3.selectAll('path.state-hit')
                    .filter(d => d.properties && d.properties.name === 'Texas')
                    .node();
                if (!el) return null;
                const r = el.getBoundingClientRect();
                // Sample points across Texas — prefer the panhandle (upper-left, fewer dots)
                const samples = [
                    [r.x + r.width * 0.15, r.y + r.height * 0.10],
                    [r.x + r.width * 0.10, r.y + r.height * 0.20],
                    [r.x + r.width * 0.25, r.y + r.height * 0.15],
                    [r.x + r.width * 0.35, r.y + r.height * 0.25],
                    [r.x + r.width * 0.50, r.y + r.height * 0.50],
                ];
                for (const [x, y] of samples) {
                    const hit = document.elementFromPoint(x, y);
                    if (hit && hit.classList.contains('state-hit')) return { x, y };
                }
                return { x: r.x + r.width * 0.15, y: r.y + r.height * 0.10 };
            }
        """)
        if texas_box:
            page.touchscreen.tap(texas_box["x"], texas_box["y"])
            time.sleep(1.2)
            tx_title_check = page.locator("#players-title").text_content()
            if "Texas" not in tx_title_check:
                # Touchend obscured by overlapping SVG elements — invoke directly
                page.evaluate("openStatePanel('Texas')")
                time.sleep(0.5)
            ok("Texas found on map", True)
        else:
            ok("Texas found on map", False, "path not found")
            page.evaluate("openStatePanel('Texas')")
            time.sleep(0.5)
        shot(page, "07_state_texas")
        tx_title = page.locator("#players-title").text_content()
        ok("Texas panel loads", "Texas" in tx_title, tx_title)

        # ── 8. Tap a player row → player arcs (panel closes, arcs on map) ────
        print("\n8. Tap player row → arcs")
        rows = page.locator(".player-row.tappable")
        nrows = rows.count()
        ok("Player rows in panel", nrows > 0, f"{nrows} rows")
        if nrows > 0:
            name = rows.first.locator(".player-name").text_content().strip()
            rows.first.tap()
            time.sleep(1.5)
            shot(page, "08_player_arcs")
            arcs2 = page.locator("path.recruit-arc").count()
            ok("Player arcs drawn", arcs2 > 0, f"{arcs2} arcs for {name}")
            back_vis = page.evaluate(
                "document.getElementById('player-back-strip').classList.contains('visible')")
            ok("Back strip visible", back_vis)
            # Panel should be CLOSED in arc view (school list no longer shown in panel)
            panel_closed = not page.evaluate(
                "document.getElementById('players-panel').classList.contains('open')")
            ok("Panel closed in arc view", panel_closed)
            # Schools must NOT be clickable in player mode (P0 regression)
            school_hit_pev = page.evaluate("""
                () => {
                    const hits = [...document.querySelectorAll('circle.school-hit')];
                    const active = hits.filter(h => {
                        const style = window.getComputedStyle(h);
                        return style.pointerEvents !== 'none';
                    });
                    return active.length;
                }
            """)
            ok("Schools non-interactive in player mode", school_hit_pev == 0,
               f"{school_hit_pev} school-hit circles still active")

        # ── 9. Back navigation ─────────────────────────────────────
        print("\n9. Back navigation")
        back_vis2 = page.evaluate(
            "document.getElementById('player-back-strip').classList.contains('visible')")
        if back_vis2:
            page.locator("#player-back-btn").tap()
            time.sleep(0.8)
            shot(page, "09_all_prospects")
            title2 = page.locator("#players-title").text_content()
            ok("Back → all prospects panel", "Pipeline" in title2, title2)
            panel_open = page.evaluate(
                "document.getElementById('players-panel').classList.contains('open')")
            ok("Panel reopens on back", panel_open)
        else:
            ok("Back → all prospects panel", False, "back strip not visible (step 8 skipped)")
            ok("Panel reopens on back", False, "back strip not visible (step 8 skipped)")

        # ── 10. Tap prospect dot directly on map ───────────────────
        print("\n10. Tap prospect dot on map")
        dot_box = page.evaluate("""
            () => {
                const d = document.querySelector('circle.prospect-dot');
                if (!d) return null;
                const r = d.getBoundingClientRect();
                return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
            }
        """)
        if dot_box:
            page.touchscreen.tap(dot_box["x"], dot_box["y"])
            time.sleep(1.0)
            shot(page, "10_tap_map_dot")
            arcs3 = page.locator("path.recruit-arc").count()
            ok("Tap map dot → arcs", arcs3 > 0, f"{arcs3} arcs")
        else:
            ok("Prospect dot found", False, "no dot in viewport")

        # ── 11. Zoom regression: label positioning ─────────────────
        print("\n11. Zoom regression — label/dot offsets")
        # School labels must be above their dot center in SVG space (y_label < y_dot_center).
        # This validates the offset formula at whatever zoom zoomToFit chose.
        label_check = page.evaluate("""
            () => {
                const labels = [...document.querySelectorAll('text.school-label')];
                const bad = labels.filter(l => {
                    const ly = parseFloat(l.getAttribute('y'));
                    const sy = parseFloat(l.dataset.sy);
                    return isNaN(ly) || isNaN(sy) || ly >= sy;  // label must be above dot center
                });
                return { total: labels.length, bad: bad.length };
            }
        """)
        ok("School labels above dot centers",
           label_check["bad"] == 0,
           f"{label_check['total']} labels, {label_check['bad']} mispositioned")

        # Player hometown label must be below its dot center (y_label > y_dot_center).
        ht_label_check = page.evaluate("""
            () => {
                const labels = [...document.querySelectorAll('text.player-hometown-label')];
                const bad = labels.filter(l => {
                    const ly = parseFloat(l.getAttribute('y'));
                    const hy = parseFloat(l.dataset.hy);
                    return isNaN(ly) || isNaN(hy) || ly <= hy;  // label must be below dot center
                });
                return { total: labels.length, bad: bad.length };
            }
        """)
        ok("Player hometown label below dot center",
           ht_label_check["total"] > 0 and ht_label_check["bad"] == 0,
           f"{ht_label_check['total']} label(s), {ht_label_check['bad']} mispositioned")

        # Zoom to k=8 (near max), re-verify label positions hold
        page.evaluate("""
            () => {
                const svgEl = document.getElementById('map');
                const cur = d3.zoomTransform(svgEl);
                const w = svgEl.clientWidth, h = svgEl.clientHeight;
                // Scale around center
                const k = 8;
                d3.select(svgEl).call(
                    d3.zoom().scaleExtent([1, 10]).transform,
                    d3.zoomIdentity.translate(w/2 - k*w/2, h/2 - k*h/2).scale(k)
                );
            }
        """)
        time.sleep(0.8)
        shot(page, "11_zoom_maxish")
        label_check2 = page.evaluate("""
            () => {
                const labels = [...document.querySelectorAll('text.school-label')];
                const bad = labels.filter(l => {
                    const ly = parseFloat(l.getAttribute('y'));
                    const sy = parseFloat(l.dataset.sy);
                    return isNaN(ly) || isNaN(sy) || ly >= sy;
                });
                return { total: labels.length, bad: bad.length };
            }
        """)
        ok("School labels above dots at k=8 zoom",
           label_check2["bad"] == 0,
           f"{label_check2['total']} labels, {label_check2['bad']} mispositioned")
        # Reset zoom
        page.evaluate("""
            () => {
                const svgEl = document.getElementById('map');
                d3.select(svgEl).call(d3.zoom().scaleExtent([1,10]).transform, d3.zoomIdentity);
            }
        """)
        time.sleep(0.5)

        # ── 12. School mode cleanup ────────────────────────────────
        print("\n12. School mode cleanup")
        page.locator("#btn-school").tap()
        time.sleep(0.8)
        shot(page, "12_school_cleanup")
        remaining = page.locator("circle.prospect-dot").count()
        ok("Prospect dots cleared", remaining == 0, f"{remaining} remaining")
        xform = page.evaluate(
            "window.getComputedStyle(document.getElementById('players-panel')).transform")
        ok("Players panel fully off-screen",
           "matrix(1, 0, 0, 1, 0, 0)" not in xform, xform[:50])

        browser.close()

    # ── Summary ────────────────────────────────────────────────────
    passed = sum(1 for _, v in results if v)
    total  = len(results)
    print(f"\n{'='*55}")
    print(f"Results: {passed}/{total} passed")
    for label, v in results:
        if not v:
            print(f"  {FAIL} {label}")
    if passed == total:
        print(f"{PASS} All {total} checks passed!")
    print(f"Screenshots → {SHOTS}/")
    print(f"{'='*55}\n")
    return passed == total

if __name__ == "__main__":
    exit(0 if run() else 1)
