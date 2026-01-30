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

# Update system packages
echo "Updating system..."
apt-get update
apt-get upgrade -y

# Install Node.js 20.x
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs git

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
sudo -u ${APP_USER} bash -c "cd ${APP_DIR}/app && npm install && npm run build"

# Set up environment
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    chown ${APP_USER}:${APP_USER} "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
    echo "⚠️  IMPORTANT: Edit ${APP_DIR}/.env and add API keys!"
fi

# Run database migrations
echo "Running database migrations..."
sudo -u ${APP_USER} bash -c "cd ${APP_DIR} && uv run alembic upgrade head"

# Create audio output directory
mkdir -p ${APP_DIR}/audio_output
chown ${APP_USER}:${APP_USER} ${APP_DIR}/audio_output

# Set up systemd service
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
ExecStartPre=/usr/local/bin/uv run alembic upgrade head
ExecStart=/usr/local/bin/uv run uvicorn api.main:app --host 127.0.0.1 --port 8246 --log-level info --no-access-log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable api
systemctl start api

echo "=========================================="
echo "Provisioning Complete: $(date)"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit ${APP_DIR}/.env with your API keys"
echo "2. Restart service: sudo systemctl restart api"
echo "3. Check logs: sudo journalctl -u api -f"
echo "4. Access app: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
