# Automated Call Center — Full Documentation

AI-powered legal call center with ElevenLabs voice, local lawllm via Ollama, and SIP trunking via LiveKit + Twilio.

## Quick Start

```bash
# 1. Start services
cd /home/lost/automated-call-center
sudo docker-compose up -d

# 2. Run tests
python3 agent/aws_mock.py

# 3. Verify services
curl http://localhost:7880        # LiveKit: OK
curl http://localhost:11434/api/tags  # Ollama: models list
```

## Status

| Service | Port | Status |
|---------|------|--------|
| LiveKit | 7880 (HTTP), 7881 (UDP) | Running |
| Redis | 6379 (TCP) | Running |
| Ollama | 11434 (TCP) | Running |
| lawllm | — | Loaded (4.1GB) |
| ElevenLabs | — | Configured (API key set) |
