"""Twilio webhook handler for the AI legal call center.

Routes inbound calls to LiveKit SIP and handles call status updates.
"""

import hmac
import hashlib
import logging
import sys
from fastapi import FastAPI, Request, Form, HTTPException
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
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WEBHOOK_URL: str = "https://your-domain.com/webhooks/twilio"
    TWILIO_STATUS_URL: str = "https://your-domain.com/webhooks/status"
    LIVEKIT_SIP_URL: str = "sip:callcenter@localhost:7881"
    AGENT_PORT: int = 8000
    WEBHOOK_SECRET: str = ""
    CORS_ORIGINS: str = ""  # comma-separated, e.g. "https://example.com"

    model_config = {"env_file": ".env"}


settings = Settings()


def _parse_cors_origins() -> list[str]:
    """Parse CORS_ORIGINS env var into a list, or return defaults."""
    if settings.CORS_ORIGINS:
        return [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    return []


def verify_twilio_signature(
    request_url: str,
    params: dict,
    twilio_signature: str,
    auth_token: str,
) -> bool:
    """Verify Twilio's X-Twilio-Signature header.

    See: https://www.twilio.com/docs/usage/webhooks/twilio-signatures
    """
    if not twilio_signature or not auth_token:
        return False

    params_str = "".join(
        f"{k}{v}" for k, v in sorted(params.items())
    )
    digest = hmac.new(
        auth_token.encode(),
        (request_url + params_str).encode(),
        hashlib.sha1,
    ).hexdigest()
    return hmac.compare_digest(digest, twilio_signature)


# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Call Center Webhook",
    description="Twilio webhook handler for the AI legal call center",
    version="0.1.0",
)

# CORS — restrict to configured origins, default to empty (no CORS) unless set
cors_origins = _parse_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["X-Twilio-Signature", "Content-Type"],
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
    # Verify Twilio signature if auth token is configured
    if settings.TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature")
        form = await request.form()
        params = dict(form)
        url = str(request.url)
        if not verify_twilio_signature(url, params, signature or "", settings.TWILIO_AUTH_TOKEN):
            logger.warning("Invalid Twilio signature from %s", from_)
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

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
    # Verify Twilio signature if auth token is configured
    if settings.TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature")
        form = await request.form()
        params = dict(form)
        url = str(request.url)
        if not verify_twilio_signature(url, params, signature or "", settings.TWILIO_AUTH_TOKEN):
            logger.warning("Invalid Twilio status signature")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    call_status_val = form.get("CallStatus", "unknown")

    logger.info("Call status: call_sid=%s status=%s", call_sid, call_status_val)

    return HTMLResponse(content="<Response></Response>", media_type="application/xml")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.AGENT_PORT)
