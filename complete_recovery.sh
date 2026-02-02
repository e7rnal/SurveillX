#!/bin/bash
# SurveillX Complete Recovery Script
# Run this when you return from college

echo "🚀 Starting SurveillX Complete Recovery..."
echo ""

# Navigate to project
cd /opt/dlami/nvme/surveillx-backend

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated"

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "⏳ Installing remaining dependencies..."
    pip install Flask Flask-CORS Flask-JWT-Extended Flask-SocketIO psycopg2-binary python-dotenv opencv-python numpy boto3 python-dateutil pytz Werkzeug
fi

echo "✅ Dependencies installed"

# Create necessary directories
mkdir -p logs clips

# Test database connection
echo "🔍 Testing database connection..."
python << 'PYEOF'
from services.db_manager import DBManager
from config import Config

try:
    db = DBManager(Config.DATABASE_URL)
    stats = db.get_dashboard_stats()
    print(f"✅ Database connected! Students: {stats['total_students']}, Alerts: {stats['recent_alerts']}")
    db.close()
except Exception as e:
    print(f"❌ Database error: {e}")
    exit(1)
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Recovery Complete!"
    echo ""
    echo "To start the application:"
    echo "  cd /opt/dlami/nvme/surveillx-backend"
    echo "  source venv/bin/activate"
    echo "  python app.py"
    echo ""
    echo "Application will run on: http://0.0.0.0:5000"
    echo "Login: admin / admin123"
    echo ""
else
    echo "❌ Recovery failed. Check errors above."
    exit 1
fi
