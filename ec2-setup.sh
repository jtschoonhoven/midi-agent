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
APP_DIR="/opt/midi-agent"
APP_USER="midi-agent"
DB_DIR="/mnt/ebs/midi-agent"
REPO_URL="https://github.com/jtschoonhoven/midi-agent.git"

# Update system packages
echo "[1/11] Updating system..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo "[2/11] Installing dependencies..."
apt-get install -y \
    git \
    python3.11 \
    python3.11-venv \
    fluidsynth \
    runit \
    curl

# Install Node.js 20.x
echo "[3/11] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install uv package manager
echo "[4/11] Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"

# Create application user
echo "[5/11] Creating application user..."
useradd -r -s /bin/bash -d ${APP_DIR} -m ${APP_USER}

# Mount EBS volume
echo "[6/11] Setting up EBS volume..."
# Wait for volume (assumes /dev/nvme1n1 - adjust if needed)
for i in {1..30}; do
    [ -e /dev/nvme1n1 ] && break
    sleep 2
done

# Format if first boot
if ! blkid /dev/nvme1n1; then
    mkfs.ext4 /dev/nvme1n1
fi

# Mount
mkdir -p /mnt/ebs
mount /dev/nvme1n1 /mnt/ebs

# Add to fstab for auto-mount on reboot
UUID=$(blkid -s UUID -o value /dev/nvme1n1)
echo "UUID=${UUID} /mnt/ebs ext4 defaults,nofail 0 2" >> /etc/fstab

# Create database directory
mkdir -p ${DB_DIR}
chown ${APP_USER}:${APP_USER} ${DB_DIR}

# Clone repository
echo "[7/11] Cloning repository..."
sudo -u ${APP_USER} git clone ${REPO_URL} ${APP_DIR}
cd ${APP_DIR}

# Install Python dependencies
echo "[8/11] Installing Python dependencies..."
sudo -u ${APP_USER} bash -c "export PATH=/root/.local/bin:\$PATH && cd ${APP_DIR} && uv sync"

# Build frontend
echo "[9/11] Building frontend..."
sudo -u ${APP_USER} bash -c "cd ${APP_DIR}/app && npm install && npm run build"

# Set up environment
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    echo "DATABASE_URL=sqlite:///${DB_DIR}/midi_agent.db" >> "${APP_DIR}/.env"
    chown ${APP_USER}:${APP_USER} "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
    echo "⚠️  IMPORTANT: Edit ${APP_DIR}/.env and add API keys!"
fi

# Run database migrations
echo "[10/11] Running database migrations..."
sudo -u ${APP_USER} bash -c "cd ${APP_DIR} && export PATH=/root/.local/bin:\$PATH && uv run alembic upgrade head"

# Create audio output directory
mkdir -p ${APP_DIR}/audio_output
chown ${APP_USER}:${APP_USER} ${APP_DIR}/audio_output

# Set up runit service
echo "[11/11] Setting up runit service..."
mkdir -p /etc/service/midi-agent-api/log
cp ${APP_DIR}/runit/midi-agent-api/run /etc/service/midi-agent-api/run
cp ${APP_DIR}/runit/midi-agent-api/log/run /etc/service/midi-agent-api/log/run
chmod +x /etc/service/midi-agent-api/run
chmod +x /etc/service/midi-agent-api/log/run

# Create log directory
mkdir -p /var/log/midi-agent-api
chown ${APP_USER}:${APP_USER} /var/log/midi-agent-api

echo "=========================================="
echo "Provisioning Complete: $(date)"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/midi-agent/.env with your API keys"
echo "2. Restart service: sudo sv restart midi-agent-api"
echo "3. Check logs: sudo tail -f /var/log/midi-agent-api/current"
echo "4. Access app: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
