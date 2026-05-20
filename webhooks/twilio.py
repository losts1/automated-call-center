from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from pydantic_settings import BaseSettings
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class Settings(BaseSettings):
    TWILIO_PHONE_NUMBER: str = "+18333841868"
    TWILIO_WEBHOOK_URL: str = "https://your-domain.com/webhooks/twilio"
    TWILIO_STATUS_URL: str = "https://your-domain.com/webhooks/status"
    WEBHOOK_SECRET: str = "webhook-secret"

settings = Settings()

@app.post("/webhooks/twilio")
async def twilio_webhook(request: Request,
                        call_sid: str = Form(None),
                        from_: str = Form(None),
                        to: str = Form(None)):
    """Handle inbound calls - route to LiveKit SIP."""
    logger.info(f"Inbound call: {call_sid} from {from_} to {to}")
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip sip:{settings.TWILIO_PHONE_NUMBER}@localhost:7881</Sip>
    </Dial>
    <Say voice="alice" language="en-us">
        Thank you for calling. Connecting you now.
    </Say>
</Response>"""
    return HTMLResponse(content=twiml, media_type="application/xml")

@app.post("/webhooks/status")
async def call_status(request: Request):
    """Handle call status updates."""
    form = await request.form()
    call_sid = form.get('CallSid', 'unknown')
    call_status = form.get('CallStatus', 'unknown')
    
    logger.info(f"Call status: {call_sid} -> {call_status}")
    
    return HTMLResponse(content="<Response></Response>", media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
