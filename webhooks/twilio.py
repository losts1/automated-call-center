"""Twilio webhook handler for the AI legal call center.

Routes inbound calls to LiveKit SIP and handles call status updates.
"""

import logging
import sys
from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic_settings import BaseSettings

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ─── Settings ─────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    TWILIO_PHONE_NUMBER: str = "+1XXXXXXXXXX"
    TWILIO_WEBHOOK_URL: str = "https://your-domain.com/webhooks/twilio"
    TWILIO_STATUS_URL: str = "https://your-domain.com/webhooks/status"
    LIVEKIT_SIP_URL: str = "sip:callcenter@localhost:7881"
    AGENT_PORT: int = 8000
    WEBHOOK_SECRET: str = "webhook-secret"

    model_config = {"env_file": ".env"}


settings = Settings()

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Call Center Webhook",
    description="Twilio webhook handler for the AI legal call center",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "service": "twilio-webhook", "version": "0.1.0"}

# ─── Webhooks ─────────────────────────────────────────────────────────────────
@app.post("/webhooks/twilio")
async def twilio_webhook(
    request: Request,
    call_sid: str = Form(None),
    from_: str = Form(None),
    to: str = Form(None),
):
    """Handle inbound calls - route to LiveKit SIP."""
    logger.info("Inbound call: call_sid=%s from=%s to=%s", call_sid, from_, to)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>{settings.LIVEKIT_SIP_URL}</Sip>
    </Dial>
    <Say voice="alice" language="en-us">
        Thank you for calling. Connecting you now.
    </Say>
</Response>"""
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.post("/webhooks/status")
async def call_status(request: Request):
    """Handle call status updates from Twilio."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    call_status = form.get("CallStatus", "unknown")

    logger.info("Call status: call_sid=%s status=%s", call_sid, call_status)

    return HTMLResponse(content="<Response></Response>", media_type="application/xml")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.AGENT_PORT)
