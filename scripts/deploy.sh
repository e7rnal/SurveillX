#!/bin/bash
# SurveillX Production Deployment Script
# Usage: sudo bash scripts/deploy.sh
set -e

PROJ_DIR="/home/ubuntu/surveillx-backend"
DOMAIN="surveillx.servebeer.com"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  SurveillX Production Deployment${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# 1. Install Nginx if not present
echo -e "\n${YELLOW}[1/6] Installing Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    apt-get update -qq
    apt-get install -y -qq nginx
    echo "  Nginx installed"
else
    echo "  Nginx already installed"
fi

# 2. Configure Nginx
echo -e "\n${YELLOW}[2/6] Configuring Nginx...${NC}"
cp "$PROJ_DIR/config/nginx.conf" /etc/nginx/sites-available/surveillx
ln -sf /etc/nginx/sites-available/surveillx /etc/nginx/sites-enabled/surveillx
rm -f /etc/nginx/sites-enabled/default
nginx -t
echo "  Nginx configured"

# 3. Install systemd services
echo -e "\n${YELLOW}[3/6] Installing systemd services...${NC}"
for svc in surveillx surveillx-ws surveillx-fastrtc surveillx-ml; do
    cp "$PROJ_DIR/config/${svc}.service" /etc/systemd/system/
    echo "  Installed ${svc}.service"
done
systemctl daemon-reload
echo "  systemd reloaded"

# 4. Create log directory
echo -e "\n${YELLOW}[4/6] Creating directories...${NC}"
mkdir -p "$PROJ_DIR/logs"
chown -R ubuntu:ubuntu "$PROJ_DIR/logs"

# 5. Kill existing manual processes
echo -e "\n${YELLOW}[5/6] Stopping manual processes...${NC}"
pkill -f "gst_streaming_server.py" 2>/dev/null || true
pkill -f "fastrtc_server.py" 2>/dev/null || true
pkill -f "app.py" 2>/dev/null || true
pkill -f "ml_worker.py" 2>/dev/null || true
sleep 2
echo "  Manual processes stopped"

# 6. Enable and start services
echo -e "\n${YELLOW}[6/6] Starting services...${NC}"
systemctl enable --now surveillx-ws
sleep 1
systemctl enable --now surveillx-fastrtc
sleep 1
systemctl enable --now surveillx
sleep 3
systemctl enable --now surveillx-ml
systemctl restart nginx
sleep 2

# Status check
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment Status${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

for svc in surveillx-ws surveillx-fastrtc surveillx surveillx-ml nginx; do
    status=$(systemctl is-active $svc 2>/dev/null)
    if [ "$status" = "active" ]; then
        echo -e "  ${GREEN}✅ $svc${NC}"
    else
        echo -e "  ❌ $svc ($status)"
    fi
done

echo ""
echo -e "${GREEN}Access your dashboard at:${NC}"
echo "  https://${DOMAIN}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  sudo systemctl status surveillx          # Flask dashboard"
echo "  sudo systemctl restart surveillx          # Restart Flask"
echo "  sudo journalctl -u surveillx -f           # Live Flask logs"
echo "  sudo systemctl restart surveillx-ml       # Restart ML worker"
echo ""
