"""
Generate the FieldTracking AWS hosting guide as a PDF.

    python -m pip install fpdf2
    python docs/build_hosting_guide.py

Output: docs/FieldTracking-AWS-Hosting-Guide.pdf
Content mirrors docs/DEPLOY_AWS.md, expanded with plain-language explanation.
"""

from pathlib import Path

from fpdf import FPDF

INK = (15, 23, 42)
INDIGO = (79, 70, 229)
SLATE = (100, 116, 139)
CODE_BG = (241, 245, 249)
RULE = (203, 213, 225)

OUT = Path(__file__).resolve().parent / "FieldTracking-AWS-Hosting-Guide.pdf"


class Guide(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SLATE)
        self.cell(0, 8, "FieldTracking - AWS Hosting Guide", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*RULE)
        self.line(self.l_margin, 16, self.w - self.r_margin, 16)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*SLATE)
        self.cell(0, 8, "Generated from docs/DEPLOY_AWS.md", align="C")


pdf = Guide(format="A4")
pdf.set_auto_page_break(auto=True, margin=16)
pdf.set_margins(18, 16, 18)
EPW = pdf.w - pdf.l_margin - pdf.r_margin


def h1(text):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*INDIGO)
    pdf.multi_cell(0, 8, text)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
    pdf.ln(4)


def h2(text):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 7, text)
    pdf.ln(1)


def p(text):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.6, text)
    pdf.ln(1.5)


def note(text):
    y0 = pdf.get_y()
    pdf.set_fill_color(255, 247, 237)
    pdf.set_font("Helvetica", "I", 9.5)
    pdf.set_text_color(120, 53, 15)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(EPW, 5.4, "  " + text, fill=True, border=0)
    pdf.ln(2)


def bullets(items):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*INK)
    for it in items:
        x = pdf.get_x()
        pdf.set_x(x + 4)
        pdf.cell(4, 5.6, chr(149))  # bullet dot
        pdf.multi_cell(EPW - 8, 5.6, it)
    pdf.ln(1.5)


def steps(items):
    pdf.set_font("Helvetica", "", 10.5)
    for i, it in enumerate(items, 1):
        pdf.set_text_color(*INDIGO)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_x(pdf.l_margin + 2)
        pdf.cell(7, 5.6, f"{i}.")
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(EPW - 9, 5.6, it)
        pdf.ln(0.5)
    pdf.ln(1.5)


def code(text):
    pdf.ln(1)
    pdf.set_font("Courier", "", 8.2)
    pdf.set_fill_color(*CODE_BG)
    pdf.set_text_color(*INK)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(EPW, 4.6, text, fill=True, border=0)
    pdf.ln(2.5)


def table(headers, rows, widths):
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_text_color(*INK)
    for hd, w in zip(headers, widths):
        pdf.cell(w, 7, hd, border=1, fill=True, align="L")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9.5)
    for row in rows:
        # measure tallest cell
        line_counts = []
        for cell, w in zip(row, widths):
            line_counts.append(len(pdf.multi_cell(w, 5, cell, dry_run=True, output="LINES")))
        h = max(line_counts) * 5
        x0, y0 = pdf.get_x(), pdf.get_y()
        for cell, w in zip(row, widths):
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(w, 5, cell, border=1, align="L", max_line_height=5)
            pdf.set_xy(x + w, y)
        pdf.set_xy(x0, y0 + h)
    pdf.ln(3)


# ── Cover ───────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.ln(32)
pdf.set_fill_color(*INDIGO)
pdf.rect(pdf.l_margin, pdf.get_y(), EPW, 34, style="F")
pdf.set_xy(pdf.l_margin, pdf.get_y() + 7)
pdf.set_font("Helvetica", "B", 24)
pdf.set_text_color(255, 255, 255)
pdf.cell(EPW, 12, "  FieldTracking", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 14)
pdf.cell(EPW, 9, "  AWS Hosting Guide - Step by Step", new_x="LMARGIN", new_y="NEXT")
pdf.ln(22)
pdf.set_text_color(*INK)
pdf.set_font("Helvetica", "", 11)
pdf.multi_cell(
    0, 6,
    "This guide walks you through hosting the FieldTracking platform (Django API, "
    "Next.js dashboard, PostgreSQL/TimescaleDB and Redis) on a single Amazon EC2 "
    "virtual machine using Docker Compose, with an Nginx reverse proxy serving "
    "everything on one address. No prior AWS or DevOps experience is assumed.",
)
pdf.ln(4)
p("Estimated time: about 15-20 minutes. Estimated cost: a small instance runs "
  "roughly a few US dollars per month (free-tier eligible for the first year on a "
  "t2/t3.micro, though 4 GB RAM is recommended).")
note("This is the HTTP-on-public-IP setup you selected. Section 11 shows how to "
     "upgrade to a domain + HTTPS, which is strongly recommended before real use.")

# ── 0. What you will build ───────────────────────────────────────────────────
pdf.add_page()
h1("1.  What you will build")
p("Everything runs on one EC2 instance. A single program called Nginx listens on "
  "the public web port (80) and quietly forwards each request to the right place:")
bullets([
    "Requests for the dashboard pages go to the Next.js web app.",
    "Requests starting with /api or /ws (live updates) go to the Django backend.",
    "The database (PostgreSQL + TimescaleDB) and Redis run alongside, but are NOT "
    "exposed to the internet - only the app can reach them.",
])
code(
    "                 +------------------ EC2 instance ------------------+\n"
    "  Browser  --80-->|  Nginx --> Next.js (web)                        |\n"
    "  Mobile   --80-->|        \\-> Django/Daphne (api) --> PostgreSQL   |\n"
    "                  |                                  \\-> Redis       |\n"
    "                  +-------------------------------------------------+"
)
p("Because the browser only ever talks to one address, there are no cross-origin "
  "problems, and the server's IP is never hard-coded into the website - so you can "
  "move servers or add a domain later without rebuilding anything.")

h2("Prerequisites")
bullets([
    "An AWS account (https://aws.amazon.com).",
    "The FieldTracking project folder (this repository).",
    "On your computer: an SSH client (built into Windows 10/11, macOS and Linux).",
    "Optional: the Flutter build setup if you want to rebuild the mobile APK.",
])

# ── 2. Launch EC2 ────────────────────────────────────────────────────────────
h1("2.  Launch the server (EC2 instance)")
steps([
    "Sign in to the AWS Console and open the EC2 service. Click 'Launch instance'.",
    "Name it 'fieldtracking'.",
    "Application and OS image (AMI): choose 'Ubuntu Server 24.04 LTS' (64-bit x86).",
    "Instance type: choose 't3.medium' (4 GB RAM, recommended). 't3.small' works "
    "for a light demo; the free-tier 't2.micro' is usable but tight.",
    "Key pair: click 'Create new key pair', give it a name, and download the .pem "
    "file. You will need it to log in - keep it safe.",
    "Network settings: click 'Edit', then under 'Firewall (security groups)' add "
    "the inbound rules in the table below.",
    "Configure storage: set 30 GB (gp3).",
    "Click 'Launch instance', then 'View all instances'.",
])
h2("Inbound firewall rules (security group)")
table(
    ["Type", "Port", "Source", "Why"],
    [
        ["SSH", "22", "My IP", "Admin login (you only)"],
        ["HTTP", "80", "Anywhere 0.0.0.0/0, ::/0", "The app, for everyone"],
    ],
    [28, 18, 70, 66],
)
note("Do NOT open ports 5432, 6379, 8000 or 3000. The database, Redis and app "
     "containers stay private and must not be reachable from the internet.")

# ── 3. Elastic IP ────────────────────────────────────────────────────────────
h1("3.  Give it a permanent IP (Elastic IP)")
p("By default a server's public IP changes if you ever stop and start it. An "
  "Elastic IP pins a fixed address so your links and the mobile app keep working.")
steps([
    "In the EC2 console left menu, open 'Elastic IPs' (under Network & Security).",
    "Click 'Allocate Elastic IP address' -> 'Allocate'.",
    "Select the new address -> 'Actions' -> 'Associate Elastic IP address'.",
    "Choose your 'fieldtracking' instance and click 'Associate'.",
])
p("Write down this address - this guide calls it EIP (for example 13.234.56.78). "
  "Wherever you see EIP below, type your real Elastic IP.")

# ── 4. Connect via SSH ───────────────────────────────────────────────────────
h1("4.  Connect to the server (SSH)")
p("Open a terminal (PowerShell on Windows, Terminal on macOS/Linux) in the folder "
  "where you saved the .pem key file, then run:")
code("ssh -i your-key.pem ubuntu@EIP")
p("On Windows, if it complains the key is too open, run this once first:")
code('icacls.exe your-key.pem /inheritance:r /grant:r "%USERNAME%:R"')
p("Type 'yes' when asked to trust the host. You are now logged into the server.")

# ── 5. Install Docker ────────────────────────────────────────────────────────
h1("5.  Install Docker")
p("Docker runs the application's containers. Paste this whole block into the SSH "
  "session:")
code(
    "sudo apt-get update\n"
    "sudo apt-get install -y ca-certificates curl git\n"
    "sudo install -m 0755 -d /etc/apt/keyrings\n"
    "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \\\n"
    "  -o /etc/apt/keyrings/docker.asc\n"
    "sudo chmod a+r /etc/apt/keyrings/docker.asc\n"
    'echo "deb [arch=$(dpkg --print-architecture) \\\n'
    '  signed-by=/etc/apt/keyrings/docker.asc] \\\n'
    "  https://download.docker.com/linux/ubuntu \\\n"
    '  $(. /etc/os-release && echo $VERSION_CODENAME) stable" \\\n'
    "  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null\n"
    "sudo apt-get update\n"
    "sudo apt-get install -y docker-ce docker-ce-cli containerd.io \\\n"
    "  docker-compose-plugin\n"
    "sudo usermod -aG docker $USER && newgrp docker"
)
p("Verify it works (should print a version number):")
code("docker --version && docker compose version")

# ── 6. Copy the project ──────────────────────────────────────────────────────
h1("6.  Put the project on the server")
p("Pick ONE of these options.")
h2("Option A - from a Git repository (if you pushed the code to GitHub)")
code("git clone <your-repository-url> fieldtracking\ncd fieldtracking")
h2("Option B - copy from your computer")
p("Run this on YOUR computer (not the server), from the project's parent folder. "
  "It securely copies the files up:")
code('scp -i your-key.pem -r "fieldtracking - Copy" ubuntu@EIP:~/fieldtracking')
p("Then back in the SSH session on the server:")
code("cd ~/fieldtracking")

# ── 7. Configure secrets ─────────────────────────────────────────────────────
h1("7.  Configure secrets (.env)")
p("Create your settings file from the template and open it in a text editor:")
code("cp .env.production.example .env\nnano .env")
p("Fill in these values, then save (in nano: Ctrl+O, Enter, Ctrl+X):")
bullets([
    "POSTGRES_PASSWORD - a strong database password.",
    "DATABASE_URL - put the SAME password inside it "
    "(postgresql://fieldtracking:THE_PASSWORD@db:5432/fieldtracking).",
    "SECRET_KEY and JWT_SECRET - one random value each.",
    "CSRF_TRUSTED_ORIGINS=http://EIP  (your Elastic IP).",
    "ALLOWED_HOSTS=EIP  (or leave it as * to allow any host).",
    "SEED_DEMO=1 to load demo users, or 0 for a clean, empty system.",
])
p("Generate the two random secrets with this command and paste the output:")
code('python3 -c "import secrets; print(secrets.token_urlsafe(50))"')

# ── 8. Build & start ─────────────────────────────────────────────────────────
h1("8.  Build and start the application")
p("This one command builds the images and starts every service in the background. "
  "The first run also sets up the database tables and (if enabled) demo data:")
code("docker compose -f docker-compose.prod.yml up -d --build")
p("Check that all five services are running:")
code("docker compose -f docker-compose.prod.yml ps")
p("Watch the backend start up (press Ctrl+C to stop watching - it keeps running):")
code("docker compose -f docker-compose.prod.yml logs -f api")

# ── 9. Open the app ──────────────────────────────────────────────────────────
h1("9.  Open the app")
p("In a browser, go to:")
code("http://EIP")
p("Interactive API documentation is at  http://EIP/api/docs/")
p("If demo data was seeded, log in with password  Password123!  using any of:")
table(
    ["Email", "Role", "Lands on"],
    [
        ["owner@fieldtracking.dev", "Platform owner", "Owner portal"],
        ["admin@acme.test", "Tenant admin", "Dashboard"],
        ["dispatch@acme.test", "Dispatcher", "Dashboard"],
        ["ravi@acme.test", "Field staff", "Mobile app"],
    ],
    [62, 40, 60],
)
note("For a real deployment, set SEED_DEMO=0 (or change these passwords) so the "
     "demo accounts do not exist on your live system.")

# ── 10. Mobile app ───────────────────────────────────────────────────────────
h1("10.  Point the mobile app at the server")
p("Rebuild the Android APK so it talks to your server. Note the address is the "
  "Elastic IP on port 80 with the /api/v1 path (Nginx routes it):")
code(
    'docker run --rm -v "$PWD/apps/mobile:/work" \\\n'
    "  -v flutter-android-sdk:/opt/android-sdk-linux \\\n"
    "  -v flutter-gradle-cache:/root/.gradle \\\n"
    "  -w /work ghcr.io/cirruslabs/flutter:stable \\\n"
    "  bash /work/build_apk.sh http://EIP/api/v1"
)
p("Install the resulting APK from apps/mobile/build/app/outputs/flutter-apk/ onto "
  "an Android phone and log in as a field-staff user. The phone needs internet "
  "access to reach the server's public IP.")

# ── 11. Day-2 operations ─────────────────────────────────────────────────────
h1("11.  Running it day to day")
h2("View logs")
code("docker compose -f docker-compose.prod.yml logs -f")
h2("Restart or stop")
code(
    "docker compose -f docker-compose.prod.yml restart\n"
    "docker compose -f docker-compose.prod.yml down"
)
h2("Deploy a new version")
code(
    "git pull            # or copy the new code up again\n"
    "docker compose -f docker-compose.prod.yml up -d --build"
)
h2("Back up the database")
code(
    "docker compose -f docker-compose.prod.yml exec -T db \\\n"
    "  pg_dump -U fieldtracking fieldtracking | gzip > backup-$(date +%F).sql.gz"
)
p("Uploaded task photos and the database live in Docker volumes (mediadata and "
  "dbdata) and survive restarts and updates. They are only deleted if you run "
  "'down -v'.")

# ── 12. Domain + HTTPS ───────────────────────────────────────────────────────
h1("12.  Upgrade to a domain + HTTPS (recommended)")
p("Running over plain HTTP is fine for a demo, but real use should be encrypted.")
steps([
    "Buy a domain and add an 'A record' pointing to your Elastic IP.",
    "Add a TLS certificate. The simplest route is a free Let's Encrypt certificate "
    "via Certbot, terminated by Nginx on port 443.",
    "In .env set SECURE_SSL=1 and CSRF_TRUSTED_ORIGINS=https://your-domain.",
    "Re-run: docker compose -f docker-compose.prod.yml up -d --build.",
    "Rebuild the APK with https://your-domain/api/v1.",
])
note("Because the website uses relative links, switching to a domain needs no "
     "website rebuild - only DNS, the certificate, and the env flag.")

# ── 13. Scaling later ────────────────────────────────────────────────────────
h1("13.  Scaling beyond one server (later)")
p("When a single machine is no longer enough, move the stateful parts to managed "
  "AWS services and keep the same container images:")
bullets([
    "PostgreSQL -> Amazon RDS (or Timescale Cloud) for managed backups/failover.",
    "Redis -> Amazon ElastiCache.",
    "Uploaded photos -> Amazon S3 (via django-storages).",
    "App containers -> Amazon ECS Fargate behind a load balancer that handles "
    "HTTPS and WebSockets, scaled to several copies.",
])
p("You would simply point DATABASE_URL and REDIS_URL at the managed endpoints; the "
  "same api and web images run unchanged.")

# ── 14. Security checklist ───────────────────────────────────────────────────
h1("14.  Security checklist")
bullets([
    "[ ] Strong, unique POSTGRES_PASSWORD, SECRET_KEY and JWT_SECRET.",
    "[ ] DEBUG=0 (the default in the template).",
    "[ ] SSH (port 22) limited to your IP; only 80/443 open to the world.",
    "[ ] Add a domain + HTTPS and set SECURE_SSL=1 before production use.",
    "[ ] Set ALLOWED_HOSTS to your host instead of * once stable.",
    "[ ] Disable or change the seeded demo accounts (SEED_DEMO=0).",
    "[ ] Schedule database backups and test restoring one.",
])

# ── 15. Troubleshooting ──────────────────────────────────────────────────────
h1("15.  Troubleshooting")
h2("The page does not load")
bullets([
    "Confirm the security group allows inbound port 80 from anywhere.",
    "Run 'docker compose -f docker-compose.prod.yml ps' - all services 'running'?",
    "Check 'docker compose -f docker-compose.prod.yml logs nginx web api'.",
])
h2("Admin login says CSRF verification failed")
bullets([
    "Set CSRF_TRUSTED_ORIGINS=http://EIP in .env, then rebuild.",
])
h2("Database errors on first start")
bullets([
    "The DATABASE_URL password must exactly match POSTGRES_PASSWORD.",
    "If you changed it after the first run, reset with "
    "'down -v' (this DELETES data) then 'up' again.",
])
h2("Mobile app cannot connect")
bullets([
    "Rebuild the APK with the correct http://EIP/api/v1 address.",
    "Make sure the phone has internet and the server's port 80 is open.",
])

pdf.output(str(OUT))
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB, {pdf.page_no()} pages)")
