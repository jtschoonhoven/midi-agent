#!/bin/bash
# EC2 User Data script for MIDI Agent
# Provisions a fresh Ubuntu instance to run the MIDI Agent application

set -e

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=========================================="
echo "MIDI Agent Provisioning"
echo "Started: $(date)"
echo "=========================================="

# Configuration
APP_DIR="/home/midi-agent"
APP_USER="midiagent"
REPO_URL="https://github.com/jtschoonhoven/midi-agent.git"
DOMAIN="${DOMAIN:-localhost}"

# Update system packages
echo "Updating system..."
apt-get update
apt-get upgrade -y

# Install Node.js 20.x
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs git

# Install Caddy
echo "Installing Caddy..."
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

# Install uv package manager
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
cp /root/.local/bin/uv /usr/local/bin/uv
cp /root/.local/bin/uvx /usr/local/bin/uvx
chmod +x /usr/local/bin/uv /usr/local/bin/uvx

# Create application user (without home dir - we'll clone into it)
echo "Creating application user..."
useradd -r -s /bin/bash -d ${APP_DIR} ${APP_USER}

# Clone repository as the app directory
echo "Cloning repository..."
git clone ${REPO_URL} ${APP_DIR}
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
cd ${APP_DIR}

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u ${APP_USER} bash -c "cd ${APP_DIR} && uv sync"

# Build frontend
echo "Building frontend..."
sudo -u ${APP_USER} bash -c "cd ${APP_DIR}/app && npm install && VITE_API_BASE_URL=https://${DOMAIN} npm run build"

# Set up environment
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    chown ${APP_USER}:${APP_USER} "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
    echo "⚠️  IMPORTANT: Edit ${APP_DIR}/.env and add API keys!"
fi

# Create audio output directory
mkdir -p ${APP_DIR}/audio_output
chown ${APP_USER}:${APP_USER} ${APP_DIR}/audio_output

# Set up systemd service for the API
echo "Setting up systemd service..."
cat > /etc/systemd/system/api.service << 'EOF'
[Unit]
Description=MIDI Agent API
After=network.target

[Service]
Type=simple
User=midiagent
WorkingDirectory=/home/midi-agent
EnvironmentFile=/home/midi-agent/.env
ExecStart=/usr/local/bin/uv run uvicorn api.main:app --host 127.0.0.1 --port 8080 --log-level info --no-access-log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Configure Caddy as reverse proxy
echo "Configuring Caddy..."
mkdir -p /etc/caddy
cat > /etc/caddy/Caddyfile << EOF
${DOMAIN} {
    reverse_proxy 127.0.0.1:8080
}
EOF

# Enable and start services
systemctl daemon-reload
systemctl enable api
systemctl start api
systemctl restart caddy

echo "=========================================="
echo "Provisioning Complete: $(date)"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit ${APP_DIR}/.env with your API keys"
echo "2. Run migrations: cd ${APP_DIR} && sudo -u ${APP_USER} uv run alembic upgrade head"
echo "3. Update domain in /etc/caddy/Caddyfile (currently: ${DOMAIN})"
echo "4. Restart services: sudo systemctl restart api && sudo systemctl restart caddy"
echo "5. Check logs: sudo journalctl -u api -f"
echo "6. Access app: https://${DOMAIN}"
