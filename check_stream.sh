#!/bin/bash
# Quick stream verification script

echo "🔍 SurveillX Stream Diagnostics"
echo "================================"
echo ""

echo "1️⃣ Server Status:"
curl -s http://localhost:5000/api/stream/config | jq -r '.current_mode' 2>/dev/null && echo "   ✅ Flask API responding" || echo "   ❌ Flask not responding"
echo ""

echo "2️⃣ ML Worker Status:"
if ps aux | grep -q "[p]ython.*ml_worker"; then
    echo "   ✅ ML Worker running"
    recent_frames=$(tail -5 logs/ml_worker.log | grep "Processed" | tail -1)
    echo "   $recent_frames"
else
    echo "   ❌ ML Worker not running"
fi
echo ""

echo "3️⃣ Recent Detections:"
detections=$(tail -30 logs/ml_worker.log | grep "📊 Pushing" | tail -3)
if [ -n "$detections" ]; then
    echo "$detections"
else
    echo "   ⚠️  No recent detections found"
fi
echo ""

echo "4️⃣ Stream Server:"
if ps aux | grep -q "[p]ython.*gst_streaming"; then
    echo "   ✅ JPEG-WS Hub running (port 8443)"
else  
    echo "   ❌ JPEG-WS Hub not running"
fi

if ps aux | grep -q "[p]ython.*fastrtc"; then
    echo "   ✅ FastRTC Hub running (port 8080)"
else
    echo "   ❌ FastRTC Hub not running"
fi
echo ""

echo "5️⃣ Active Camera Connections:"
camera_status=$(tail -10 logs/ws_hub.log 2>/dev/null | grep "Camera client" | tail -2)
if [ -n "$camera_status" ]; then
    echo "$camera_status"
else
    echo "   ⚠️  No recent camera connections"
fi
echo ""

echo "================================"
echo "💡 Next: Open browser to http://surveillx.servebeer.com:5000"
echo "   Then go to Live Monitor and click Connect"
