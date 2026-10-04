# Deploying FieldTracking to AWS (single EC2 + Docker Compose)

This runs the whole stack on **one EC2 instance** with Docker Compose, behind
an Nginx reverse proxy on port 80:

```
                    ┌────────────────── EC2 instance ──────────────────┐
  Browser  ──:80──► │  Nginx ──► Next.js (web:3000)                     │
  Mobile   ──:80──► │        └─► Django/Daphne (api:8000) ──► Postgres  │
                    │                                      └─► Redis     │
                    └───────────────────────────────────────────────────┘
```

Only port 80 is public. Postgres, Redis, the API and the web app talk to each
other on Docker's private network. The browser uses **one origin** (the EC2
IP), so there's no CORS and the IP is never baked into the web build.

> This guide is the **HTTP-on-public-IP** path. See *“Add a domain + HTTPS”*
> at the end to upgrade to `https://your-domain` — strongly recommended before
> real use.

---

## 1. Launch the EC2 instance

1. EC2 → **Launch instance**.
2. **AMI:** Ubuntu Server 24.04 LTS (x86_64).
3. **Type:** `t3.medium` (4 GB RAM recommended — TimescaleDB + Redis + API +
   web + Nginx are tight on 2 GB). `t3.small` works for a light demo.
4. **Key pair:** create/download one for SSH.
5. **Storage:** 30 GB gp3.
6. **Security group** — inbound rules:
   | Type | Port | Source | Why |
   |---|---|---|---|
   | SSH | 22 | **My IP** | admin access |
   | HTTP | 80 | 0.0.0.0/0 (and ::/0) | the app |

   Do **not** open 5432/6379/8000/3000 — they stay internal.
7. After it boots, **Allocate an Elastic IP** and associate it with the
   instance (so the public IP survives stop/start). Call it `EIP` below.

## 2. Install Docker

SSH in (`ssh -i your-key.pem ubuntu@EIP`) and run:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker   # run docker without sudo
```

## 3. Get the code onto the instance

Either `git clone <your repo>` or copy it up from your machine:

```bash
# from your laptop, in the project's parent folder
scp -i your-key.pem -r "fieldtracking - Copy" ubuntu@EIP:~/fieldtracking
```

Then on the server: `cd ~/fieldtracking`.

## 4. Configure secrets

```bash
cp .env.production.example .env
nano .env
```

Set, at minimum:
- `POSTGRES_PASSWORD` — a strong password, and the **same** password inside
  `DATABASE_URL`.
- `SECRET_KEY` and `JWT_SECRET` — generate each with
  `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.
- `CSRF_TRUSTED_ORIGINS=http://EIP` (your Elastic IP).
- `ALLOWED_HOSTS=EIP` (or leave `*`).
- `SEED_DEMO=1` to load the demo tenant/users (set `0` for a clean install).

## 5. Build and start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

First boot runs migrations, converts `LocationLog` to a Timescale hypertable,
collects static files, and (if `SEED_DEMO=1`) seeds demo data. Check it:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api    # Ctrl-C to stop
curl -s http://localhost/api/v1/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@acme.test","password":"Password123!"}'
```

Open **http://EIP** in a browser. Demo logins (password `Password123!`):
`owner@fieldtracking.dev`, `admin@acme.test`, `dispatch@acme.test`,
`ravi@acme.test`, `priya@acme.test`.

API docs: **http://EIP/api/docs/**

## 6. Point the mobile app at the server

Rebuild the APK with the EC2 origin (note: port 80, path `/api/v1` — Nginx
routes it):

```bash
docker run --rm -v "$PWD/apps/mobile:/work" \
  -v flutter-android-sdk:/opt/android-sdk-linux -v flutter-gradle-cache:/root/.gradle \
  -w /work ghcr.io/cirruslabs/flutter:stable \
  bash /work/build_apk.sh http://EIP/api/v1
```

Because the server is HTTP (no TLS yet), the app keeps cleartext enabled, which
the build already sets. Install the APK and log in as a field-staff user.

## 7. Day-2 operations

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f

# Restart / stop
docker compose -f docker-compose.prod.yml restart
docker compose -f docker-compose.prod.yml down

# Deploy a new version
git pull            # or scp the new code
docker compose -f docker-compose.prod.yml up -d --build

# Database backup (run on a schedule / before upgrades)
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U fieldtracking fieldtracking | gzip > backup-$(date +%F).sql.gz
```

Uploaded task photos live in the `mediadata` volume and the database in
`dbdata`; both survive `up`/`down`. They are deleted only by
`docker compose ... down -v`.

---

## Add a domain + HTTPS (recommended next step)

1. Buy a domain (Route 53 or any registrar) and add an **A record** →
   your Elastic IP.
2. Put the app behind a TLS proxy. Easiest is to add an Nginx + Certbot
   companion (e.g. `nginxproxy/acme-companion`) or run Certbot on the host and
   mount the certs into the Nginx container, listening on 443.
3. In `.env`, set `SECURE_SSL=1` and
   `CSRF_TRUSTED_ORIGINS=https://your-domain`, then
   `docker compose -f docker-compose.prod.yml up -d --build`.
4. Rebuild the APK with `https://your-domain/api/v1`.

Since the web app already uses **relative** URLs, switching to a domain needs
**no web rebuild** — only DNS, certs, and the env flag.

## Scaling beyond one box (later)

When one instance isn't enough, lift the stateful pieces out:
- **Postgres → Amazon RDS** (or Timescale Cloud) — managed backups/failover.
- **Redis → Amazon ElastiCache.**
- **Media → Amazon S3** via `django-storages` (swap the `default` storage
  backend; remove the local `/media/` Nginx route).
- **App tier → ECS Fargate** behind an ALB (the ALB handles WebSockets and
  TLS), running the same `api` and `web` images, scaled to N tasks.

Point `DATABASE_URL` / `REDIS_URL` at the managed endpoints and the same
images run unchanged.

## Security checklist

- [ ] Strong, unique `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET`.
- [ ] `DEBUG=0` (default here).
- [ ] SSH (22) restricted to your IP; only 80/443 open to the world.
- [ ] Add a domain + HTTPS and set `SECURE_SSL=1` before production use.
- [ ] Set `ALLOWED_HOSTS` to your host (not `*`) once stable.
- [ ] Change/disable the seeded demo accounts (`SEED_DEMO=0`) for a real tenant.
- [ ] Schedule database backups and test a restore.
