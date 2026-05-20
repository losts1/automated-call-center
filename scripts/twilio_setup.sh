#!/usr/bin/env bash
#
# Twilio SIP Trunk Setup for LiveKit + Call Center
# Prerequisites: Twilio CLI (twilio) installed and authenticated
#
# Usage:
#   ./scripts/twilio_setup.sh
#

set -e

# ─── Configuration ───
ACCOUNT_SID="${TWILIO_ACCOUNT_SID:?Please set TWILIO_ACCOUNT_SID env var or add to .env}"
AUTH_TOKEN="${TWILIO_AUTH_TOKEN:?Please set TWILIO_AUTH_TOKEN env var or add to .env}"
PHONE_NUMBER="${TWILIO_PHONE_NUMBER:?Please set TWILIO_PHONE_NUMBER env var or add to .env}"
LIVEKIT_SIP_DOMAIN="callcenter.livekit.io"
SIP_USERNAME="callcenter"
SIP_PASSWORD="$(openssl rand -hex 16)"
PHONE_NUMBER="+18333841868"

echo "=== Twilio SIP Trunk Setup ==="
echo ""
echo "Account SID:    $ACCOUNT_SID"
echo "Phone Number:   $PHONE_NUMBER"
echo "SIP Domain:     $LIVEKIT_SIP_DOMAIN"
echo "SIP Username:   $SIP_USERNAME"
echo "SIP Password:   $SIP_PASSWORD"
echo ""
echo "NOTE: The phone number +18333841868 needs to be purchased/configured in the Twilio Console first."
echo ""

# ─── Step 1: Verify Twilio CLI ───
if ! command -v twilio &> /dev/null; then
    echo "❌ Twilio CLI not installed. Install with:"
    echo "   npm install -g twilio-cli"
    echo "   twilio login"
    exit 1
fi

# ─── Step 2: Check phone number ───
echo "📞 Checking phone number..."
twilio api:core:phone-numbers:v2:list \
    --account-sid="$ACCOUNT_SID" \
    --phone-number="$PHONE_NUMBER" \
    --output json 2>/dev/null || echo "  Phone number not found (must be purchased in console)"

echo ""
echo "=== Manual Configuration Required ==="
echo ""
echo "1. Go to Twilio Console: https://console.twilio.com/"
echo "2. Purchase/assign phone number: +18333841868"
echo "3. Under 'Voice & Fax' → 'TwiML' → 'SIP Trunk':"
echo "   - SIP URL: sip:${LIVEKIT_SIP_DOMAIN}:7880"
echo "   - Auth: Basic (${SIP_USERNAME}:${SIP_PASSWORD})"
echo ""
echo "4. Configure LiveKit SIP Trunk:"
echo "   - Add to docker-compose.yml:"
echo "     environment:"
echo "       - TWILIO_SIP_DOMAIN=${LIVEKIT_SIP_DOMAIN}"
echo "       - TWILIO_SIP_USERNAME=${SIP_USERNAME}"
echo "       - TWILIO_SIP_PASSWORD=${SIP_PASSWORD}"
echo ""
echo "5. Restart LiveKit:"
echo "   sudo docker compose restart livekit"
echo ""
echo "=== Setup Complete ==="
