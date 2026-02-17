#!/usr/bin/env python3
"""
Test Detection Flow
Tests the complete detection pipeline: ML Worker → Flask → SocketIO → Browser
"""

import time
import requests
import json

FLASK_URL = "http://localhost:5000"

def test_detection_endpoint():
    """Test if Flask detection endpoint is accessible."""
    print("🧪 Testing Flask detection endpoint...")
    
    # Mock detection data
    test_data = {
        'faces': [
            {
                'student_id': None,
                'student_name': 'Unknown',
                'confidence': 0,
                'location': {'top': 100, 'right': 300, 'bottom': 400, 'left': 100},
                'age': 25
            }
        ],
        'activity': {
            'type': 'normal',
            'is_abnormal': False,
            'severity': 'low',
            'confidence': 0,
            'description': ''
        },
        'timestamp': time.time()
    }
    
    try:
        response = requests.post(
            f"{FLASK_URL}/api/stream/detections",
            json=test_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ Flask endpoint responsive")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Flask returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        return False


def test_health():
    """Test if Flask server is healthy."""
    print("\n🧪 Testing Flask health...")
    
    try:
        response = requests.get(f"{FLASK_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Flask server healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            print(f"   Students: {data.get('stats', {}).get('total_students', 0)}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return False


def check_ml_worker_logs():
    """Check ML Worker logs for detection activity."""
    print("\n📋 Checking ML Worker logs...")
    
    try:
        with open('logs/ml_worker.log', 'r') as f:
            lines = f.readlines()
            recent = lines[-30:]  # Last 30 lines
            
            detection_lines = [l for l in recent if '📊' in l or 'detection' in l.lower() or 'face' in l.lower()]
            
            if detection_lines:
                print(f"✅ Found {len(detection_lines)} detection-related log entries:")
                for line in detection_lines[-5:]:  # Show last 5
                    print(f"   {line.strip()}")
            else:
                print("⚠️  No detection logs found in recent entries")
                print("   ML Worker may not be processing frames yet")
                
    except FileNotFoundError:
        print("❌ ML Worker log file not found")
    except Exception as e:
        print(f"❌ Error reading logs: {e}")


def check_flask_logs():
    """Check Flask logs for detection activity."""
    print("\n📋 Checking Flask logs...")
    
    try:
        with open('logs/flask.log', 'r') as f:
            lines = f.readlines()
            recent = lines[-30:]
            
            detection_lines = [l for l in recent if '📥' in l or '📤' in l or 'detection' in l.lower()]
            
            if detection_lines:
                print(f"✅ Found {len(detection_lines)} detection-related log entries:")
                for line in detection_lines[-5:]:
                    print(f"   {line.strip()}")
            else:
                print("⚠️  No detection logs found in recent entries")
                
    except FileNotFoundError:
        print("❌ Flask log file not found")
    except Exception as e:
        print(f"❌ Error reading logs: {e}")


def main():
    print("=" * 60)
    print("  Detection Flow Test")
    print("=" * 60)
    
    # Test 1: Health check
    health_ok = test_health()
    
    # Test 2: Detection endpoint
    endpoint_ok = test_detection_endpoint()
    
    # Test 3: Check logs
    check_ml_worker_logs()
    check_flask_logs()
    
    print("\n" + "=" * 60)
    print("  Test Summary")
    print("=" * 60)
    print(f"Flask Health:       {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Detection Endpoint: {'✅ PASS' if endpoint_ok else '❌ FAIL'}")
    print("\n💡 Next Steps:")
    print("   1. Open browser to http://localhost:5000")
    print("   2. Go to Live Monitor")
    print("   3. Click Connect")
    print("   4. Open browser console (F12)")
    print("   5. Look for: '🔌 Setting up detection listener'")
    print("   6. Point camera at face and check for '📥 Detection event received!'")
    print("\n📁 Monitor logs with: tail -f logs/*.log")
    

if __name__ == '__main__':
    main()
