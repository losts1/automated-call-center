# Automated Call Center

AI-powered legal call center with ElevenLabs voice, local lawllm via Ollama, and SIP trunking via LiveKit + Twilio.

## Status ✅

| Service | Port | Status |
|---------|------|--------|
| LiveKit | 7880 (HTTP), 7881 (UDP) | Running |
| Redis | 6379 (TCP) | Running |
| Ollama | 11434 (TCP) | Running (lawllm loaded) |
| ElevenLabs | — | Configured (API key set) |
| Twilio | — | Account active (+18333841868) |

## Quick Start

```bash
# Start services
cd /home/lost/automated-call-center
sudo docker-compose up -d

# Verify services
curl http://localhost:7880        # LiveKit: OK
curl http://localhost:11434/api/tags  # Ollama: models list
python3 agent/aws_mock.py        # Run tests
```

## Twilio SIP Setup

### Current State
- ✅ Phone number +18333841868 configured in account
- ⏳ Webhook endpoint needs public URL
- ⏳ Phone number needs webhook URL update

### Setup Steps

1. **Start webhook server:**
   ```bash
   python3 webhooks/twilio.py
   ```

2. **Create public URL** (choose one):
   - **Ngrok:** `ngrok http 8000` (requires account signup)
   - **Cloudflare Tunnel:** `cloudflared tunnel --url http://localhost:8000`
   - **HTTPS domain:** Configure your own domain with HTTPS

3. **Update phone number:**
   ```bash
   TWILIO_WEBHOOK_URL=https://your-domain.com/webhooks/twilio python3 scripts/configure_twilio.py
   ```

### Webhook Endpoints

- **Inbound Calls:** `/webhooks/twilio` - Routes call to LiveKit SIP
- **Status Callbacks:** `/webhooks/status` - Call status updates

### Architecture

```
PSTN → Twilio → SIP Trunk → LiveKit → Telephony Agent
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
            ElevenLabs TTS      lawllm (Ollama)     LiveKit Webhooks
            (Turbo v2.5)        (Local)            → moto DynamoDB/S3
                    │                    │
                    └────────────────────┼────────────────────┘
                                         │
                                    Call State & Recordings
                                    (moto/in-process mock)
```

## Testing

```bash
# Run all tests
python3 agent/aws_mock.py

# Expected output:
# ✅ Setup resources
# ✅ Full lifecycle test
# ✅ StateManager test
# ✅ RecordingManager test
# ✅ All tests passed!
```
