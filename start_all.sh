#!/bin/bash
# ============================================
#  SurveillX — Service Manager
# ============================================
# Usage:
#   bash start_all.sh          # Start all services
#   bash start_all.sh stop     # Stop all services
#   bash start_all.sh status   # Check service status
#   bash start_all.sh restart  # Restart all services

set -e
cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

mkdir -p logs pids

# ---- Configuration ----
FLASK_PORT=5000

# ---- Helper Functions ----

kill_by_pid_file() {
    local pidfile="$1"
    local name="$2"
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            sleep 0.5
            # Force kill if still alive
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null
            fi
            echo "   ✅ Stopped $name (PID $pid)"
        fi
        rm -f "$pidfile"
    fi
}

kill_by_pattern() {
    local pattern="$1"
    local name="$2"
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            kill "$pid" 2>/dev/null || true
        done
        sleep 0.5
        # Force kill survivors
        for pid in $pids; do
            kill -9 "$pid" 2>/dev/null || true
        done
        echo "   ✅ Stopped $name (PIDs: $pids)"
    fi
}

kill_by_port() {
    local port="$1"
    local pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || true
        sleep 0.5
        kill -9 $pid 2>/dev/null || true
    fi
}

# ---- Stop ----
stop_all() {
    echo "🛑 Stopping all SurveillX services..."

    # 1. Stop by PID files
    kill_by_pid_file "pids/flask.pid" "Flask Server"
    kill_by_pid_file "pids/ml_worker.pid" "ML Worker"

    # 2. Stop by process pattern (catches anything started outside the script)
    kill_by_pattern "python3.*app\.py" "Flask (by pattern)"
    kill_by_pattern "python3.*ml_worker\.py" "ML Worker (by pattern)"
    kill_by_pattern "python3.*fastrtc_server" "FastRTC (legacy)"
    kill_by_pattern "python3.*gst_streaming" "GStreamer Hub (legacy)"

    # 3. Force-clear known ports
    kill_by_port $FLASK_PORT

    # Clean PID files
    rm -f pids/*.pid

    echo ""
    echo "✅ All services stopped."

    # Verify
    local remaining=$(ss -tlnp 2>/dev/null | grep -E ":${FLASK_PORT}\b" || true)
    if [ -n "$remaining" ]; then
        echo "⚠️  Warning: Port $FLASK_PORT still in use:"
        echo "   $remaining"
    fi
}

# ---- Status ----
status_all() {
    echo "📊 SurveillX Service Status"
    echo "─────────────────────────────────────"

    # Check Flask
    if [ -f "pids/flask.pid" ] && kill -0 $(cat pids/flask.pid) 2>/dev/null; then
        echo "   ✅ Flask Server     — running (PID $(cat pids/flask.pid))"
    else
        local flask_pid=$(pgrep -f "python3.*app\.py" 2>/dev/null | head -1 || true)
        if [ -n "$flask_pid" ]; then
            echo "   ✅ Flask Server     — running (PID $flask_pid, no pidfile)"
        else
            echo "   ❌ Flask Server     — stopped"
        fi
    fi

    # Check ML Worker
    if [ -f "pids/ml_worker.pid" ] && kill -0 $(cat pids/ml_worker.pid) 2>/dev/null; then
        echo "   ✅ ML Worker        — running (PID $(cat pids/ml_worker.pid))"
    else
        local ml_pid=$(pgrep -f "python3.*ml_worker\.py" 2>/dev/null | head -1 || true)
        if [ -n "$ml_pid" ]; then
            echo "   ✅ ML Worker        — running (PID $ml_pid, no pidfile)"
        else
            echo "   ❌ ML Worker        — stopped"
        fi
    fi

    echo "─────────────────────────────────────"
    echo "Ports:"
    ss -tlnp 2>/dev/null | grep -E ":${FLASK_PORT}\b" || echo "   No SurveillX ports bound"
    echo ""
}

# ---- Start ----
start_all() {
    echo "🚀 Starting SurveillX Services..."
    echo "─────────────────────────────────────"

    # 1. Flask Dashboard + API (port 5000)
    echo -n "   [1/2] Flask Dashboard (port $FLASK_PORT)... "
    nohup python3 app.py > logs/flask.log 2>&1 &
    echo $! > "pids/flask.pid"
    echo "PID $!"

    # 2. Wait for Flask to start, then launch ML Worker
    sleep 3
    echo -n "   [2/2] ML Worker... "
    nohup python3 services/ml_worker.py > logs/ml_worker.log 2>&1 &
    echo $! > "pids/ml_worker.pid"
    echo "PID $!"

    echo "─────────────────────────────────────"
    echo ""

    # Wait and verify
    sleep 2
    local flask_running=false
    if kill -0 $(cat pids/flask.pid) 2>/dev/null; then
        flask_running=true
    fi

    if $flask_running; then
        echo "✅ All services started successfully!"
        echo ""
        # Try to get public IP, fallback to hostname
        local ip=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo "   📺 Dashboard:  http://${ip}:${FLASK_PORT}"
        echo "   📁 Logs:       tail -f logs/flask.log"
        echo "   🛑 Stop:       bash start_all.sh stop"
        echo "   📊 Status:     bash start_all.sh status"
    else
        echo "❌ Flask failed to start! Check logs:"
        echo "   tail -20 logs/flask.log"
        exit 1
    fi
}

# ---- Main ----
case "${1:-start}" in
    stop)    stop_all ;;
    status)  status_all ;;
    start)   stop_all 2>/dev/null; echo ""; start_all ;;
    restart) stop_all; echo ""; start_all ;;
    *)       echo "Usage: bash start_all.sh [start|stop|status|restart]" ;;
esac
