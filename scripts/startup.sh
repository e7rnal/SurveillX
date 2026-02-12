#!/bin/bash
# SurveillX Startup Script
# Updates all IP-dependent configurations on EC2 boot

set -e

LOG_FILE="/home/ubuntu/surveillx-backend/logs/startup.log"
echo "$(date): Starting SurveillX startup script..." >> $LOG_FILE

# Get current public IP - try multiple methods
PUBLIC_IP=""

# Method 1: AWS IMDSv2 (token-based)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || true)
if [ -n "$TOKEN" ]; then
    PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
fi

# Method 2: AWS IMDSv1 (fallback)
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
fi

# Method 3: External service (fallback)
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s --connect-timeout 5 https://api.ipify.org 2>/dev/null || true)
fi

# Method 4: Another external service
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s --connect-timeout 5 https://ifconfig.me 2>/dev/null || true)
fi

if [ -z "$PUBLIC_IP" ]; then
    echo "$(date): ERROR - Could not get public IP from any method" >> $LOG_FILE
    exit 1
fi

echo "$(date): Public IP: $PUBLIC_IP" >> $LOG_FILE

# 1. Update DuckDNS
echo "$(date): Updating DuckDNS..." >> $LOG_FILE
curl -s "https://www.duckdns.org/update?domains=surveillx&token=fc1aa3a3-a836-4cbb-bf93-c9503adb9ca7&ip=$PUBLIC_IP" >> $LOG_FILE
echo "" >> $LOG_FILE

# 2. Update TURN server config
echo "$(date): Updating TURN server config..." >> $LOG_FILE
cat > /etc/turnserver.conf << EOF
# Coturn TURN server configuration for SurveillX
# Auto-generated on boot

# Public IP of this server
external-ip=$PUBLIC_IP

# Listening ports
listening-port=3478
tls-listening-port=5349

# Relay ports range
min-port=49152
max-port=65535

# Authentication
lt-cred-mech
user=surveillx:surveillx2026

# Realm
realm=surveillx.local

# Logging
log-file=/var/log/turnserver.log
verbose

# Performance
total-quota=100
stale-nonce=600

# Disable TCP relay
no-tcp-relay

# Fingerprinting
fingerprint
EOF

# 3. Restart TURN server
echo "$(date): Restarting TURN server..." >> $LOG_FILE
systemctl restart coturn 2>> $LOG_FILE || true

# 4. Update .env file with current IP (for reference)
if [ -f /home/ubuntu/surveillx-backend/.env ]; then
    sed -i "s/^PUBLIC_IP=.*/PUBLIC_IP=$PUBLIC_IP/" /home/ubuntu/surveillx-backend/.env 2>/dev/null || \
    echo "PUBLIC_IP=$PUBLIC_IP" >> /home/ubuntu/surveillx-backend/.env
fi

echo "$(date): Startup script completed successfully" >> $LOG_FILE
echo "$(date): DuckDNS hostname: surveillx.servebeer.com" >> $LOG_FILE
echo "$(date): TURN server: $PUBLIC_IP:3478" >> $LOG_FILE
