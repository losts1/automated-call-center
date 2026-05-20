#!/usr/bin/env bash
#
# Setup webhook server and ngrok tunnel for Twilio
#
set -e

echo "=== Twilio Webhook Setup ==="
echo ""

# Start webhook server in background
echo "Starting webhook server..."
cd /home/lost/automated-call-center
python3 webhooks/twilio.py &
WEBHOOK_PID=$!
echo "Webhook server PID: $WEBHOOK_PID"

# Wait for server to start
sleep 3

# Check if port 8000 is listening
if ! ss -tlnp | grep -q ":8000"; then
    echo "❌ Webhook server failed to start"
    exit 1
fi

echo "✅ Webhook server running on port 8000"
echo ""

# Start ngrok tunnel
echo "Starting ngrok tunnel..."
ngrok http 8000 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
echo "Ngrok PID: $NGROK_PID"

# Wait for tunnel to be ready
sleep 5

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL"
    echo "Check /tmp/ngrok.log for errors"
    exit 1
fi

echo "✅ Ngrok tunnel ready: $NGROK_URL"
echo ""
echo "=== Configuration ==="
echo "Webhook URL: $NGROK_URL/webhooks/twilio"
echo "Status URL: $NGROK_URL/webhooks/status"
echo ""
echo "=== Next Steps ==="
echo "1. Update phone number with webhook URLs (run configure_twilio.py)"
echo "2. Test call to +18333841868"
echo "3. Monitor logs for call status"
echo ""
echo "To stop: kill $WEBHOOK_PID $NGROK_PID"
