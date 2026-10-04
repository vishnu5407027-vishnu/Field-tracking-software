"""
Generate the FieldTracking project report (for submission) as a PDF, embedding
the real screenshots from docs/screenshots/.

    python -m pip install fpdf2 pillow
    python docs/build_project_report.py
Output: docs/FieldTracking-Project-Report.pdf
"""

from pathlib import Path

from fpdf import FPDF
from PIL import Image

INK = (15, 23, 42)
INDIGO = (79, 70, 229)
SLATE = (100, 116, 139)
CODE_BG = (241, 245, 249)
RULE = (203, 213, 225)

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
OUT = HERE / "FieldTracking-Project-Report.pdf"


class Report(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SLATE)
        self.cell(0, 8, "FieldTracking - Project Report", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*RULE)
        self.line(self.l_margin, 16, self.w - self.r_margin, 16)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*SLATE)
        self.cell(0, 8, "Field Tracking System for Sales Executives", align="C")


pdf = Report(format="A4")
pdf.set_auto_page_break(auto=True, margin=16)
pdf.set_margins(18, 16, 18)
EPW = pdf.w - pdf.l_margin - pdf.r_margin


def h1(text):
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*INDIGO)
    pdf.multi_cell(0, 8, text)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
    pdf.ln(3.5)


def h2(text):
    pdf.ln(1.5)
    pdf.set_font("Helvetica", "B", 11.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 6.5, text)
    pdf.ln(1)


def p(text):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.6, text)
    pdf.ln(1.5)


def bullets(items):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*INK)
    for it in items:
        x = pdf.get_x()
        pdf.set_x(x + 4)
        pdf.cell(4, 5.6, chr(149))
        pdf.multi_cell(EPW - 8, 5.6, it)
    pdf.ln(1.5)


def code(text):
    pdf.ln(1)
    pdf.set_font("Courier", "", 8.0)
    pdf.set_fill_color(*CODE_BG)
    pdf.set_text_color(*INK)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(EPW, 4.4, text, fill=True)
    pdf.ln(2.5)


def table(headers, rows, widths):
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 9.2)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_text_color(*INK)
    for hd, w in zip(headers, widths):
        pdf.cell(w, 7, hd, border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9.2)
    for row in rows:
        counts = [len(pdf.multi_cell(w, 4.8, c, dry_run=True, output="LINES"))
                  for c, w in zip(row, widths)]
        rh = max(counts) * 4.8
        if pdf.get_y() + rh > pdf.h - 16:
            pdf.add_page()
        x0, y0 = pdf.get_x(), pdf.get_y()
        for c, w in zip(row, widths):
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(w, 4.8, c, border=1, max_line_height=4.8)
            pdf.set_xy(x + w, y)
        pdf.set_xy(x0, y0 + rh)
    pdf.ln(3)


def figure(name, caption):
    path = SHOTS / f"{name}.png"
    if not path.exists():
        return
    iw, ih = Image.open(path).size
    aspect = iw / ih
    w = EPW
    h = w / aspect
    max_h = 150
    if h > max_h:
        h = max_h
        w = h * aspect
    if pdf.get_y() + h + 10 > pdf.h - 16:
        pdf.add_page()
    x = pdf.l_margin + (EPW - w) / 2
    pdf.image(str(path), x=x, w=w, h=h)
    pdf.set_draw_color(*RULE)
    pdf.rect(x, pdf.get_y() - h, w, h)
    pdf.ln(1.5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(0, 5, caption, align="C")
    pdf.ln(4)


# ── Cover ───────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.ln(26)
pdf.set_fill_color(*INDIGO)
pdf.rect(pdf.l_margin, pdf.get_y(), EPW, 40, style="F")
pdf.set_xy(pdf.l_margin, pdf.get_y() + 8)
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(255, 255, 255)
pdf.cell(EPW, 14, "  Field Tracking System", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 15)
pdf.cell(EPW, 10, "  for Sales Executives", new_x="LMARGIN", new_y="NEXT")
pdf.ln(26)
pdf.set_text_color(*INK)
pdf.set_font("Helvetica", "", 11)
pdf.multi_cell(0, 6,
    "A multi-tenant, real-time field-staff tracking and management platform: a "
    "Python/Django REST + WebSocket backend, a Next.js web dashboard, and a "
    "Flutter mobile app for field staff.")
pdf.ln(8)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 7, "Project report", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)
pdf.set_font("Helvetica", "", 11)
for line in ["Submitted by : ______________________________",
             "Roll number  : ______________________________",
             "Guide        : ______________________________",
             "Date         : ______________________________"]:
    pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*SLATE)
pdf.multi_cell(0, 5, "Technologies: Python, Django, Django REST Framework, Django "
    "Channels, PostgreSQL + TimescaleDB, Redis, Next.js (React), TailwindCSS, "
    "Leaflet, Flutter, Docker, AWS.")

# ── 1. Abstract ─────────────────────────────────────────────────────────────
pdf.add_page()
h1("1.  Abstract")
p("In today's fast-paced business environment, organizations rely heavily on "
  "field sales teams to drive revenue and maintain customer relationships. "
  "Managing and monitoring field executives efficiently remains a significant "
  "challenge due to the lack of real-time tracking and structured reporting. The "
  "Field Tracking System for Sales Executives addresses this with a comprehensive, "
  "mobile-first solution for tracking and managing field activities.")
p("The mobile application is built with Flutter for a high-performance, "
  "cross-platform experience on Android and iOS. The backend is implemented in "
  "Python using the Django REST Framework, providing a secure, scalable, API-based "
  "architecture, with Django Channels adding real-time WebSocket communication. A "
  "Next.js web dashboard gives managers a live operational picture.")
p("The system focuses on real-time location tracking of sales executives, daily "
  "activity logging, attendance (clock in/out), geofenced site check-ins, task "
  "dispatch with photographic proof of work, route playback, and performance "
  "analytics. Security and data integrity are maintained through JWT authentication, "
  "role-based access control, and strict per-tenant data isolation. The platform is "
  "containerized with Docker for reliable, repeatable deployment to the cloud.")

# ── 2. Objectives ───────────────────────────────────────────────────────────
h1("2.  Objectives")
bullets([
    "Track the real-time location of field staff on a live map.",
    "Record attendance through shift clock-in / clock-out.",
    "Dispatch tasks with a location and capture proof of work (photos, notes).",
    "Detect site arrivals/departures automatically using geofences.",
    "Replay a worker's route for any day with distance and active/idle time.",
    "Provide performance analytics per staff member (visits, tasks, distance).",
    "Enforce secure, role-based access and isolate each organization's data.",
    "Support many organizations (multi-tenant SaaS) under one platform owner.",
])

# ── 3. Technology stack ─────────────────────────────────────────────────────
h1("3.  Technology Stack")
table(["Layer", "Technology"], [
    ["Backend API", "Python, Django 5, Django REST Framework"],
    ["Realtime", "Django Channels (ASGI / Daphne) + Redis channel layer"],
    ["Database", "PostgreSQL 16 + TimescaleDB (location hypertable)"],
    ["Live cache", "Redis (latest position per worker, geofence state)"],
    ["Authentication", "JSON Web Tokens (djangorestframework-simplejwt)"],
    ["Web dashboard", "Next.js 14 (React), TypeScript, TailwindCSS, Leaflet"],
    ["Mobile app", "Flutter (Dart): geolocator, sqflite, image_picker"],
    ["Maps & geo", "OpenStreetMap tiles, Photon geocoding, OSRM routing"],
    ["Deployment", "Docker, Docker Compose, Nginx, AWS EC2"],
], [42, 130])

# ── 4. System architecture ──────────────────────────────────────────────────
h1("4.  System Architecture")
p("All clients communicate with a single Django service that speaks both HTTP "
  "(REST) and WebSockets (via Channels). Redis holds each worker's latest position "
  "for an O(1) live map read and powers real-time fan-out to dashboards. "
  "PostgreSQL stores relational data, with high-volume GPS history kept in a "
  "TimescaleDB hypertable. In production, Nginx fronts everything on one origin.")
code(
    "[Flutter mobile app]                 [Next.js web dashboard]\n"
    "      |  REST + WebSocket                   ^  REST + WebSocket\n"
    "      v                                     |\n"
    "  [ Django REST + Channels (Daphne, ASGI) ]-+\n"
    "      |-> Redis        latest location, geofence state, fan-out\n"
    "      |-> PostgreSQL   relational data + TimescaleDB location history\n"
    "      '-> WebSocket    broadcast to tenant group:\n"
    "                       location_sync . geofence_event . task_updated"
)
h2("Ping lifecycle")
p("The mobile app buffers GPS pings in a local SQLite queue, then flushes them to "
  "the API. The server stores each batch, overwrites the worker's entry in the "
  "Redis live cache, diffs geofence containment to emit ENTER/EXIT events, and "
  "broadcasts updates to that tenant's dashboard group only. If the device is "
  "offline, pings wait in the queue and sync automatically when back online.")

# ── 5. Multi-tenancy & RBAC ─────────────────────────────────────────────────
h1("5.  Multi-tenancy and Roles")
p("The platform is multi-tenant: one deployment serves many organizations. Every "
  "tenant-owned record carries a tenant id, and the API scopes all queries to the "
  "caller's tenant (read from the verified JWT, never from the request), so one "
  "organization can never see another's data. Access is governed by four roles:")
table(["Role", "Capabilities"], [
    ["Super Admin (owner)", "Owner portal: create/suspend tenants, platform analytics, MRR"],
    ["Tenant Admin", "Manage team (invite, edit, reset passwords, roles, delete); all dispatcher rights"],
    ["Dispatcher", "Live map, route playback, task dispatch, geofences, performance"],
    ["Field Staff", "Mobile app: own tasks, clock in/out, location upload, proof capture"],
], [42, 130])

# ── 6. Modules / Features ───────────────────────────────────────────────────
h1("6.  Modules and Features")
h2("Authentication & profile")
p("JWT login with role-based redirection. Every user can manage their own profile "
  "and change their password; tenant admins can edit any member and reset passwords.")
h2("Real-time live map")
p("Managers see every on-duty worker as a named avatar marker that moves in real "
  "time. A searchable staff finder lists all field staff; selecting one flies the "
  "map to their current location. Open task locations and geofences are overlaid.")
h2("Attendance & tracking")
p("Workers clock in to start a shift; the app then tracks location in the "
  "background (foreground service) and stops on clock-out, clearing the live "
  "marker. Tracking only ever runs during an open shift, protecting battery and "
  "privacy.")
h2("Task dispatch & proof of work")
p("Dispatchers create tasks and place them on the map (with worldwide place "
  "search). Field staff advance task status (assigned -> en route -> in progress -> "
  "completed), add notes, and attach photos captured with the device camera.")
h2("Geofencing")
p("Circular site boundaries trigger automatic check-in / check-out events when a "
  "worker enters or leaves, producing an auditable visit log.")
h2("Route playback & analytics")
p("Any worker's route for a chosen day can be replayed with total distance and an "
  "active/idle split. A performance report summarizes site visits, completed tasks, "
  "distance covered, active time, and hours on shift per staff member.")

# ── 7. Screenshots ──────────────────────────────────────────────────────────
pdf.add_page()
h1("7.  Application Screenshots")
p("The following are screenshots of the running application.")
figure("01-login", "Figure 1: Secure login with role-based redirection.")
figure("02-live-map", "Figure 2: Real-time Live Map - avatar markers, searchable "
       "staff finder, and the live worker count.")
figure("03-task-dispatch", "Figure 3: Task dispatch with map-based location picker "
       "and worldwide place search.")
figure("04-task-detail-active", "Figure 4: Active task - the worker's live position "
       "and the road route with ETA to the destination.")
figure("05-task-detail-completed", "Figure 5: Completed task - travelled route, "
       "photographic proof of work, and work notes.")
figure("06-geofences", "Figure 6: Geofence management and the check-in / check-out log.")
figure("07-route-playback", "Figure 7: Route playback with distance and active/idle split.")
figure("08-performance", "Figure 8: Per-staff performance analytics.")
figure("09-team-management", "Figure 9: Team management - invite, edit, reset "
       "password, change role, and remove members.")
figure("10-profile", "Figure 10: Self-service profile and password management.")
figure("11-owner-portal", "Figure 11: Platform owner portal - tenants, seats, and MRR.")

# ── 8. Key API endpoints ────────────────────────────────────────────────────
h1("8.  Key API Endpoints")
p("The REST API is versioned under /api/v1. A representative subset:")
table(["Method & path", "Purpose"], [
    ["POST /auth/login", "Authenticate, return JWT + user"],
    ["GET  /me  .  POST /me/password", "Own profile / change password"],
    ["GET  /locations/live", "Current positions of on-duty staff (live map)"],
    ["POST /staff/locations", "Upload a batch of GPS pings"],
    ["GET  /locations/history", "Route playback for a user and date"],
    ["GET/POST /tasks  .  GET /tasks/{id}/route", "Dispatch board / task route + live"],
    ["PATCH /staff/tasks/{id}  .  /photo", "Advance status / attach camera photo"],
    ["GET/POST /geofences  .  /geofences/events", "Geofences and visit log"],
    ["GET  /reports/performance", "Per-staff productivity report"],
    ["GET/POST /owner/tenants", "Owner: list / provision tenants"],
], [70, 102])
p("Interactive API documentation (Swagger UI) is served at /api/docs/.")

# ── 9. Security ─────────────────────────────────────────────────────────────
h1("9.  Security")
bullets([
    "JWT-based stateless authentication; passwords hashed with Django's hasher.",
    "Role-based permissions enforced on every endpoint.",
    "Strict per-tenant data isolation derived from the token, never the request.",
    "WebSocket connections are authenticated and locked to one tenant group.",
    "Secrets supplied via environment variables; DEBUG disabled in production.",
    "HTTPS, secure cookies and HSTS enabled by a single flag behind a TLS proxy.",
])

# ── 10. Testing ─────────────────────────────────────────────────────────────
h1("10.  Testing")
p("The backend is covered by an automated pytest suite (40+ tests) spanning "
  "authentication, role permissions, tenant isolation, attendance, location "
  "ingestion and the live cache, geofence ENTER/EXIT detection, route history and "
  "performance, task dispatch and proof upload, profile and admin user management, "
  "and the real-time broadcast payload. The web app builds clean under the Next.js "
  "production compiler and the Flutter app passes static analysis.")

# ── 11. Deployment ──────────────────────────────────────────────────────────
h1("11.  Deployment")
p("The whole platform is containerized. A development stack starts with a single "
  "command; a production stack adds an Nginx reverse proxy that serves the web app, "
  "REST API, WebSockets, admin, and uploaded media on one origin.")
code("docker compose -f docker-compose.prod.yml up -d --build")
p("It is designed to run on a single AWS EC2 instance (with PostgreSQL/TimescaleDB "
  "and Redis as containers), and can later scale out to managed AWS services - "
  "Amazon RDS, ElastiCache, S3 and ECS Fargate - without code changes. A detailed, "
  "step-by-step hosting guide accompanies this report.")

# ── 12. Future enhancements ─────────────────────────────────────────────────
h1("12.  Future Enhancements")
bullets([
    "Subscription billing (the data model and MRR are already in place).",
    "Push notifications for new task assignments and SLA breaches.",
    "Object storage (S3) and a CDN for proof photos at scale.",
    "Optimized routing and ETA using a dedicated routing/maps provider.",
    "Customer/visit management and digital signature capture.",
    "Offline-first dashboard and richer analytics dashboards.",
])

# ── 13. Conclusion ──────────────────────────────────────────────────────────
h1("13.  Conclusion")
p("The Field Tracking System provides a practical, end-to-end solution for managing "
  "field sales operations. By combining a robust Django backend, real-time "
  "communication, a modern web dashboard, and a cross-platform Flutter app, it "
  "improves transparency, accountability, and decision-making. Its secure, "
  "multi-tenant, containerized architecture makes it reliable to operate and ready "
  "to grow - a demonstration of modern application development applied to a "
  "real-world business problem.")

pdf.output(str(OUT))
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB, {pdf.page_no()} pages)")
