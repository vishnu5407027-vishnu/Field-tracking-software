"""Capture real screenshots of the running dashboard for the project report.

Prereq: dev stack up (web :3000, api :8000) and docs/_prep_demo_data.py run.
    python -m pip install playwright && python -m playwright install chromium
    python docs/_capture_screens.py
Outputs PNGs to docs/screenshots/.
"""

import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

WEB = "http://localhost:3000"
API = "http://localhost:8000/api/v1"
OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)


def api_get(path, token):
    req = urllib.request.Request(API + path)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def token(email):
    req = urllib.request.Request(
        API + "/auth/login", method="POST",
        data=json.dumps({"email": email, "password": "Password123!"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())["accessToken"]


def main():
    admin = token("admin@acme.test")
    tasks = api_get("/tasks", admin)
    # Richest completed task (the one with proof photos/notes).
    done = [t for t in tasks if t["status"] == "COMPLETED"]
    completed = max(done, key=lambda t: len(t.get("proofs", [])))["id"] if done else None
    # Prefer an EN_ROUTE task (has a live worker + route line).
    active = None
    for st in ("EN_ROUTE", "IN_PROGRESS", "ASSIGNED"):
        match = next((t["id"] for t in tasks if t["status"] == st), None)
        if match:
            active = match
            break

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = ctx.new_page()

        def login(email):
            page.goto(f"{WEB}/login", wait_until="networkidle")
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', "Password123!")
            page.get_by_role("button", name="Sign in").click()
            page.wait_for_url("**/dashboard**" if email != "owner@fieldtracking.dev"
                              else "**/owner**", timeout=15000)
            page.wait_for_timeout(1500)

        def shot(name, full=False, wait=1500):
            page.wait_for_timeout(wait)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            print("captured", name)

        # Login screen (logged out)
        page.goto(f"{WEB}/login", wait_until="networkidle")
        shot("01-login")

        # Tenant admin / dispatcher views
        login("admin@acme.test")
        page.goto(f"{WEB}/dashboard", wait_until="networkidle")
        shot("02-live-map", wait=4500)  # let tiles + markers render

        page.goto(f"{WEB}/dashboard/tasks", wait_until="networkidle")
        shot("03-task-dispatch", full=True, wait=4000)

        if active:
            page.goto(f"{WEB}/dashboard/tasks/{active}", wait_until="networkidle")
            shot("04-task-detail-active", full=True, wait=5000)
        if completed:
            page.goto(f"{WEB}/dashboard/tasks/{completed}", wait_until="networkidle")
            shot("05-task-detail-completed", full=True, wait=5000)

        page.goto(f"{WEB}/dashboard/geofences", wait_until="networkidle")
        shot("06-geofences", full=True, wait=4000)

        # Route playback: pick the first staff option, load.
        page.goto(f"{WEB}/dashboard/playback", wait_until="networkidle")
        page.wait_for_timeout(1500)
        try:
            sel = page.locator("select").first
            opts = sel.locator("option")
            if opts.count() > 1:
                sel.select_option(index=1)
            page.get_by_role("button", name="Load route").click()
        except Exception as e:
            print("playback interaction skipped:", e)
        shot("07-route-playback", wait=4500)

        page.goto(f"{WEB}/dashboard/performance", wait_until="networkidle")
        shot("08-performance", full=True, wait=2500)

        page.goto(f"{WEB}/dashboard/staff", wait_until="networkidle")
        shot("09-team-management", full=True, wait=2000)

        page.goto(f"{WEB}/profile", wait_until="networkidle")
        shot("10-profile", full=True, wait=2000)

        # Owner portal (separate login)
        ctx.clear_cookies()
        page.goto(f"{WEB}/login", wait_until="networkidle")
        page.evaluate("() => localStorage.clear()")
        login("owner@fieldtracking.dev")
        page.goto(f"{WEB}/owner", wait_until="networkidle")
        shot("11-owner-portal", full=True, wait=2500)

        browser.close()
    print("All screenshots in", OUT)


if __name__ == "__main__":
    main()
