#!/bin/bash
# ============================================
#  SurveillX — Start All Services
# ============================================
# Usage: bash start_all.sh
#   Stop: bash start_all.sh stop
#   Status: bash start_all.sh status

set -e
cd "$(dirname "$0")"
source venv/bin/activate
mkdir -p logs

# ---- PID file locations ----
PID_DIR="./pids"
mkdir -p "$PID_DIR"

stop_all() {
    echo "🛑 Stopping all SurveillX services..."
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "   Stopped $name (PID $pid)"
        else
            echo "   $name already stopped"
        fi
        rm -f "$pidfile"
    done
    echo "✅ All services stopped."
}

status_all() {
    echo "📊 SurveillX Service Status"
    echo "─────────────────────────────────────"
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            echo "   ✅ $name (PID $pid) — running"
        else
            echo "   ❌ $name (PID $pid) — dead"
        fi
    done
    echo "─────────────────────────────────────"
    echo "Ports:"
    ss -tlnp 2>/dev/null | grep -E ":(5000|8080|8443)" || echo "   No ports bound"
}

start_all() {
    echo "🚀 Starting SurveillX Services..."
    echo "─────────────────────────────────────"

    # 1. JPEG-WS Streaming Hub (port 8443)
    echo -n "   [1/4] JPEG-WS Hub (port 8443)... "
    python3 gst_streaming_server.py > logs/ws_hub.log 2>&1 &
    echo $! > "$PID_DIR/ws_hub.pid"
    echo "PID $!"

    # 2. FastRTC Streaming Hub (port 8080)
    echo -n "   [2/4] FastRTC Hub (port 8080)... "
    python3 fastrtc_server.py > logs/fastrtc.log 2>&1 &
    echo $! > "$PID_DIR/fastrtc.pid"
    echo "PID $!"

    # 3. Flask Dashboard + API (port 5000)
    echo -n "   [3/4] Flask Dashboard (port 5000)... "
    python3 app.py > logs/flask.log 2>&1 &
    echo $! > "$PID_DIR/flask.pid"
    echo "PID $!"

    # 4. ML Worker (connects to WS hub)
    sleep 2  # Wait for servers to bind ports
    echo -n "   [4/4] ML Worker... "
    python3 services/ml_worker.py > logs/ml_worker.log 2>&1 &
    echo $! > "$PID_DIR/ml_worker.pid"
    echo "PID $!"

    echo "─────────────────────────────────────"
    echo "✅ All services started!"
    echo ""
    echo "📺 Dashboard: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP'):5000"
    echo "📁 Logs:      tail -f logs/*.log"
    echo "🛑 Stop:      bash start_all.sh stop"
    echo "📊 Status:    bash start_all.sh status"
}

# ---- Main ----
case "${1:-start}" in
    stop)   stop_all ;;
    status) status_all ;;
    start)  stop_all 2>/dev/null; start_all ;;
    *)      echo "Usage: bash start_all.sh [start|stop|status]" ;;
esac
