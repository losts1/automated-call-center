#!/usr/bin/env bash
#
# Complete Twilio setup: webhook server, ngrok tunnel, phone number config
#
set -e

echo "=== Twilio Setup ==="
echo ""

# Start webhook server
echo "Starting webhook server..."
cd /home/lost/automated-call-center
python3 webhooks/twilio.py &
WEBHOOK_PID=$!
sleep 3

# Start ngrok
echo "Starting ngrok tunnel..."
ngrok http 8000 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 5

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL"
    cat /tmp/ngrok.log
    exit 1
fi

echo "✅ Ngrok: $NGROK_URL"

# Update phone number
echo "Configuring phone number..."
python3 scripts/configure_twilio.py

echo ""
echo "=== Setup Complete ==="
echo "Webhook: $NGROK_URL/webhooks/twilio"
echo "Status: $NGROK_URL/webhooks/status"
echo ""
echo "PIDs: $WEBHOOK_PID $NGROK_PID"
echo "To stop: kill $WEBHOOK_PID $NGROK_PID"
