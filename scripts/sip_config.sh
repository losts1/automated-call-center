#!/usr/bin/env bash
#
# SIP Trunk Configuration for Twilio + LiveKit
# Run this to configure the SIP trunk connection.
#
# Requirements:
#   - Twilio account with Programmable Voice enabled
#   - Twilio phone number with Voice capability
#   - LiveKit server running and accessible
#

set -euo pipefail

# ─── Configuration ───
LIVEKIT_URL="wss://your-livekit-domain.livekit.cloud"  # or http://localhost:7880 for local
LIVEKIT_API_KEY="${LIVEKIT_API_KEY:-devkey}"
LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET:-secretkey}"
TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID:-}"
TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN:-}"
TWILIO_PHONE_NUMBER="${TWILIO_PHONE_NUMBER:-}"

echo "╔══════════════════════════════════════════════════╗"
echo "║        Twilio SIP Trunk Setup                    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─── Step 1: Create SIP Domain on Twilio ───
echo "Step 1: Create SIP Domain on Twilio"
echo "  → Go to Twilio Console > Programmable Voice > Trunks"
echo "  → Click 'Create new SIP trunk'"
echo "  → Set SIP domain: yourdomain.sip.twilio.com"
echo "  → Set SIP secure: TLS"
echo ""
read -p "  Press Enter when SIP domain is created..."

# ─── Step 2: Add SIP Trunk to LiveKit ───
echo ""
echo "Step 2: Register SIP trunk with LiveKit"
echo ""
echo "  Export your Twilio credentials:"
echo "  export LIVEKIT_SIP_TRUNK_ADDRESS='yourdomain.sip.twilio.com'"
echo "  export LIVEKIT_SIP_TRUNK_AUTH_USERNAME='your_twilio_sip_user'"
echo "  export LIVEKIT_SIP_TRUNK_AUTH_PASSWORD='your_twilio_sip_password'"
echo ""
echo "  Create the SIP trunk in LiveKit:"
echo "  livekit-cli sip create-trunk \\"
echo "    --address \$LIVEKIT_SIP_TRUNK_ADDRESS \\"
echo "    --auth-username \$LIVEKIT_SIP_TRUNK_AUTH_USERNAME \\"
echo "    --auth-password \$LIVEKIT_SIP_TRUNK_AUTH_PASSWORD \\"
echo "    --inbound-numbers '+1.*'"
echo ""
read -p "  Press Enter when SIP trunk is registered..."

# ─── Step 3: Configure Dispatch Rules ───
echo ""
echo "Step 3: Configure LiveKit Dispatch Rules"
echo "  → Set dispatch rule to route to your agent room"
echo "  → Room name pattern: call-{call_id}"
echo "  → Agent identity: legal-assistant"
echo ""

# ─── Step 4: Set up TwiML for Phone Number ───
echo ""
echo "Step 4: Configure Twilio Phone Number"
echo "  → Go to Twilio Console > Phone Numbers > Manage > Active numbers"
echo "  → Select your phone number"
echo "  → Voice configuration: SIP"
echo "  → SIP URL: sip:yourdomain.sip.twilio.com"
echo ""
read -p "  Press Enter when phone number is configured..."

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║        Setup Complete!                           ║"
echo "║                                                  ║"
echo "║  Test by calling your Twilio number.             ║"
echo "║  Calls will route: PSTN → Twilio → SIP → LiveKit ║"
echo "╚══════════════════════════════════════════════════╝"
