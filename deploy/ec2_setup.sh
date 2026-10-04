#!/usr/bin/env bash
# One-shot EC2 bootstrap for FieldTracking (single host, HTTP on the public IP).
# Run from the project root on the server:
#     bash deploy/ec2_setup.sh
# Re-runnable: installs Docker if missing, then (re)builds and starts the stack.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "ERROR: .env not found in $(pwd). Copy .env.production.example to .env first." >&2
  exit 1
fi

# ── Install Docker + compose plugin if not present ───────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl git
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  elif command -v dnf >/dev/null 2>&1; then
    # Amazon Linux 2023 / Fedora
    sudo dnf install -y docker git
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    ARCH=$(uname -m)
    sudo curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  else
    echo "Unsupported OS: install Docker + the compose plugin manually." >&2
    exit 1
  fi
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
  echo "==> Docker installed. (You may need to log out/in for non-sudo docker.)"
fi

# Use sudo for compose if the current shell isn't in the docker group yet.
DC="docker"
if ! docker info >/dev/null 2>&1; then DC="sudo docker"; fi

echo "==> Building and starting the stack..."
$DC compose -f docker-compose.prod.yml up -d --build

echo
echo "==> Status:"
$DC compose -f docker-compose.prod.yml ps
echo
echo "Done. Open  http://$(curl -s ifconfig.me 2>/dev/null || echo YOUR_EC2_IP)/"
echo "Demo logins use password: Password123!"
