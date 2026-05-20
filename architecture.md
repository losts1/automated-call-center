# Automated Call Center — Architecture

## System Overview

```
PSTN → Twilio Phone Number → Twilio SIP Trunk → LiveKit Server
                                                    │
                              ┌───────────────────────┼──────────────────────────────────────────────────────┐
                              │                       │                       │                              │
                              ▼                       ▼                       ▼                              │
                      [Inbound Agent]           [Outbound Agent]        [Queue/Bot]                     │
                              │                       │                       │                              │
                              │  ┌────────────────────┴────────────────────┐ │                              │
                              │  │                                         │ │                              │
                              │  ▼                                         ▼ │                              │
                              │  ElevenLabs TTS                    ElevenLabs STT  │                              │
                              │  (Turbo v2.5, ~69 w/s)            (Scribe v2)      │                              │
                              │  │                                         │ │                              │
                              │  └────────────────────┬────────────────────┘ │                              │
                              │                       │                       │                              │
                              ▼                       ▼                       │                              │
                        Conversation             Conversation              │                              │
                        Intelligence Layer       Intelligence Layer        │                              │
                        (lawllm, Ollama)         (lawllm, Ollama)         │                              │
                        (localhost:11434)        (localhost:11434)        │                              │
                              │                       │                       │                              │
                              └───────────────────────┼───────────────────────┼──────────────────────────────┘
                                              │       │                       │                              │
                                              ▼       ▼                       ▼                              ▼
                                      ┌─────────────────────────────┐  ┌──────────────┐  ┌────────────────────┐
                                      │    moto (In-Process Mock)     │  │  LiveKit     │  │  Webhook Events     │
                                      │  S3 → Recording storage       │  │  Redis       │  │  (State tracking)   │
                                      │  DynamoDB → Call state        │  │  Session     │  │                     │
                                      │  SQS → Async tasks            │  │  Data        │  │                     │
                                      │  SNS → Notifications          │  │              │  │                     │
                                      └─────────────────────────────┘  └──────────────┘  └────────────────────┘
```

## Component Breakdown

### 1. Twilio — PSTN Gateway
- **Inbound:** Twilio phone number → SIP Trunk → LiveKit room
- **Outbound:** LiveKit SIP outbound → Twilio → PSTN
- **Cost:** ~$1.00/mo per number + ~$0.013/min

### 2. LiveKit Server — Session Management
- **LiveKit Cloud** or self-hosted via Docker
- Handles WebRTC rooms, SIP bridging, participant lifecycle
- **Telephony Plugin:** SIP trunk inbound/outbound, call routing
- **Agents SDK:** Real-time voice agent framework

### 3. Voice Agent (Python) — Core Logic
```
┌─────────────────────────────────────────────────┐
│              LiveKit Telephony Agent             │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ ElevenLabs│    │  lawllm  │    │  moto    │  │
│  │   STT    │◄──►│ (Ollama) │◄──►│ S3/DDB   │  │
│  │ (Scribe v2)│   │          │    │ (In-proc)│  │
│  └──────────┘    └──────────┘    └──────────┘  │
│         │            │                           │
│         └────────────┼───────────────────────────┘
│                      │
│              ┌───────▼───────┐
│              │ ElevenLabs TTS│
│              │  (Turbo v2.5) │
│              └───────────────┘
│
│  Features:
│  - Multi-turn conversation with interrupt handling
│  - Legal domain knowledge (lawllm model)
│  - Call recording (S3 via moto)
│  - Real-time transcription
│  - Sentiment analysis
│  - Intent detection
│  - SIP call transfer
│  - Call disposition tracking
└─────────────────────────────────────────────────┘
```

### 4. lawllm via Ollama — Local Conversation Intelligence
- Runs on Ollama at localhost:11434
- Handles:
  - Natural language legal Q&A
  - Intent classification (complaint, inquiry, appointment, escalation)
  - Sentiment/emotion detection
  - Compliance monitoring (recording notices, opt-out handling)
  - Follow-up generation and next-best-action
  - Call summarization

### 5. moto — In-Process AWS Mock
- **S3:** Call recordings storage (WAV/FLAC)
- **DynamoDB:** Call state, session metadata, dispositions
- **SQS:** Async task queue (recording processing, notifications)
- **SNS:** Event notifications (webhooks to admin dashboard)
- Runs in-process — no Docker needed

## Call Flow (Inbound)

```
1. Customer calls Twilio number
2. Twilio routes via SIP Trunk to LiveKit
3. LiveKit creates room → dispatches to agent
4. Agent initializes:
   - ElevenLabs STT starts listening
   - lawllm loads conversation context
   - moto DynamoDB creates call record
5. Greeting plays ("Thank you for calling...")
6. Customer speaks → STT transcribes → lawllm processes → TTS responds
7. Agent handles conversation flow:
   - Intent detection → routing action
   - If escalation → transfer to human (SIP)
   - If resolution → disposition + callback
8. Call ends → recording saved to S3
9. Call metadata + transcript → DynamoDB
10. SQS triggers post-call processing:
    - Transcript summary
    - Sentiment analysis
    - Compliance check
    - Notification to admin
```

## Tech Stack Summary

| Component | Technology | Location | Cost |
|-----------|-----------|----------|------|
| PSTN | Twilio | Cloud | ~$1/mo + per-min |
| Session Management | LiveKit | Cloud/Self-hosted | Free tier or $100+/mo |
| STT | ElevenLabs Scribe v2 | Cloud | $0.033/min |
| TTS | ElevenLabs Turbo v2.5 | Cloud | $0.30/1k chars |
| Conversation AI | lawllm via Ollama | Local (localhost) | $0 |
| Recording Storage | moto S3 | In-process | $0 |
| State Management | moto DynamoDB | In-process | $0 |
| Async Processing | moto SQS | In-process | $0 |
| Notifications | moto SNS | In-process | $0 |

## Next Steps

1. ✅ Architecture design
2. ✅ AWS mock (moto) setup and tests
3. ✅ LLM client (lawllm/Ollama) integration
4. ✅ State manager and recording manager
5. 🔄 LiveKit server deployment
6. 🔄 ElevenLabs API key configuration
7. 🔄 Twilio SIP trunk setup
8. 🔄 Webhook handler
9. 🔄 End-to-end integration test
