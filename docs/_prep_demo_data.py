"""Populate the running dev stack with realistic data for documentation
screenshots: live worker positions, an active task with a route, a completed
task with a note + photo, geofence check-ins, and route history for playback."""

import io
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone

B = "http://localhost:8000/api/v1"


def call(method, path, token=None, body=None):
    req = urllib.request.Request(B + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=20) as r:
            return r.status, json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or "null")


def upload_photo(path, token, png_bytes):
    boundary = "----ftdoc"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
        f"filename=\"site.png\"\r\nContent-Type: image/png\r\n\r\n".encode()
        + png_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(B + path, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status


def login(email):
    _, b = call("POST", "/auth/login", body={"email": email, "password": "Password123!"})
    return b["accessToken"]


def ping(lat, lng, mins_ago, speed=4.0, battery=80):
    at = datetime.now(timezone.utc) - timedelta(minutes=mins_ago)
    return {"lat": lat, "lng": lng, "speed": speed, "batteryLevel": battery,
            "recordedAt": at.isoformat()}


def make_photo():
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (640, 460), (226, 232, 240))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 640, 70], fill=(79, 70, 229))
        d.text((20, 26), "FieldTracking - On-site proof photo", fill=(255, 255, 255))
        d.rectangle([40, 120, 600, 300], outline=(100, 116, 139), width=3)
        d.text((60, 200), "AC unit - Block B, 3rd floor (inspected)", fill=(15, 23, 42))
        d.text((20, 420), datetime.now().strftime("Captured %Y-%m-%d %H:%M"),
               fill=(100, 116, 139))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        return bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000d49444154789c63f8cfc0f01f0005000100ff5f6c8c000000004945"
            "4e44ae426082"
        )


def main():
    admin = login("admin@acme.test")
    ravi = login("ravi@acme.test")
    priya = login("priya@acme.test")

    _, users = call("GET", "/users", admin)
    by_email = {u["email"]: u["id"] for u in users}
    ravi_id, priya_id = by_email["ravi@acme.test"], by_email["priya@acme.test"]

    # Clock both workers in.
    for t in (ravi, priya):
        call("PATCH", "/staff/clock", t, {"action": "in"})

    # Ravi: a route over the last ~25 min ending inside the Technopark geofence
    # (drives live marker, route playback, and a geofence check-in).
    path = [
        (8.5500, 76.8700, 25), (8.5512, 76.8730, 22), (8.5525, 76.8755, 19),
        (8.5538, 76.8775, 16), (8.5549, 76.8792, 12), (8.5558, 76.8802, 8),
        (8.5564, 76.8808, 4), (8.5566, 76.8810, 1),
    ]
    call("POST", "/staff/locations", ravi,
         {"pings": [ping(la, ln, m) for la, ln, m in path]})

    # Priya: live somewhere else in the city.
    call("POST", "/staff/locations", priya, {"pings": [ping(8.5705, 76.8900, 2, speed=0)]})

    # A few extra tasks for a fuller dispatch board.
    due = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    call("POST", "/tasks", admin, {"title": "Router replacement", "address": "Infosys SEZ, Technopark Phase 1",
         "lat": 8.5571, "lng": 76.8795, "fieldStaffId": priya_id, "dueAt": due})
    call("POST", "/tasks", admin, {"title": "CCTV maintenance", "address": "Phase 3, Technocity",
         "lat": 8.5612, "lng": 76.8702, "dueAt": due})

    # Active task for Priya -> EN_ROUTE (shows live position + route line on detail).
    _, t_active = call("POST", "/tasks", admin, {"title": "Generator service",
        "address": "Thejaswini Building, Technopark", "lat": 8.5559, "lng": 76.8826,
        "fieldStaffId": priya_id, "dueAt": due})
    call("PATCH", f"/staff/tasks/{t_active['id']}", priya, {"status": "EN_ROUTE"})

    # Completed task for Ravi with a route, a note and a photo.
    _, t_done = call("POST", "/tasks", admin, {"title": "AC unit inspection",
        "address": "Block B, Technopark Campus", "lat": 8.5566, "lng": 76.8810,
        "fieldStaffId": ravi_id, "dueAt": due})
    call("PATCH", f"/staff/tasks/{t_done['id']}", ravi, {"status": "EN_ROUTE"})
    time.sleep(3)
    now = datetime.now(timezone.utc)
    seg = [
        {"lat": 8.5560 + i * 0.0002, "lng": 76.8804 + i * 0.0002,
         "speed": 3.0, "recordedAt": (now - timedelta(seconds=6 - i)).isoformat()}
        for i in range(6)
    ]
    call("POST", "/staff/locations", ravi, {"pings": seg})
    call("POST", f"/staff/tasks/{t_done['id']}/proofs", ravi,
         {"type": "NOTE", "content": "Quarterly maintenance done. Replaced air filter and "
          "checked refrigerant levels. Unit running normally."})
    print("photo upload:", upload_photo(f"/staff/tasks/{t_done['id']}/photo", ravi, make_photo()))
    call("PATCH", f"/staff/tasks/{t_done['id']}", ravi, {"status": "COMPLETED"})

    print("Active task id :", t_active["id"])
    print("Completed task :", t_done["id"])
    print("Done seeding documentation data.")


if __name__ == "__main__":
    main()
