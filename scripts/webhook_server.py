"""
LiveKit Webhook Server
Handles room events and updates call state via moto/local AWS mock.
"""

import asyncio
import base64
import hashlib
import hmac
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from livekit.api import TokenVerifier
from rich.console import Console

from config.settings import settings
from agent.state_manager import StateManager

app = FastAPI(title="Call Center Webhooks")
console = Console()
state = StateManager()

# LiveKit signs each webhook with a JWT (HS256, iss=API key) in the
# Authorization header, carrying a base64 sha256 hash of the request body.
# Verify the JWT via the official SDK; check the body hash ourselves so we
# stay decoupled from LiveKit's event proto schema.
_token_verifier = (
    TokenVerifier(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    if settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET
    else None
)
if _token_verifier is None:
    console.print(
        "[yellow]⚠ LIVEKIT_API_KEY/SECRET not set — webhook signature "
        "verification is DISABLED[/yellow]"
    )


def verify_livekit_signature(raw_body: bytes, auth_token: str) -> bool:
    """Verify a LiveKit webhook's Authorization JWT and body hash.

    Returns True when verification is disabled (no credentials configured).
    """
    if _token_verifier is None:
        return True
    if not auth_token:
        return False
    try:
        claims = _token_verifier.verify(auth_token)
    except Exception:
        return False
    if not claims.sha256:
        return False
    return hmac.compare_digest(
        hashlib.sha256(raw_body).digest(),
        base64.b64decode(claims.sha256),
    )


@app.post("/webhooks/livekit")
async def livekit_webhook(request: Request):
    """Handle LiveKit room events."""
    raw_body = await request.body()
    auth_token = request.headers.get("Authorization", "")
    if not verify_livekit_signature(raw_body, auth_token):
        console.print("[red]⛔ Rejected LiveKit webhook: invalid signature[/red]")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = json.loads(raw_body)
    event_type = data.get("event", "unknown")
    room = data.get("room", {})
    participant = data.get("participant", {})

    call_id = room.get("custom_id", "unknown")

    console.print(f"\n[bold yellow]📡 LiveKit Event: {event_type}[/bold yellow]")
    console.print(f"   Call ID: {call_id}")
    console.print(f"   Room: {room.get('name', 'N/A')}")
    console.print(f"   Participant: {participant.get('identity', 'N/A')}")

    if event_type == "room_started":
        await handle_room_started(call_id, room, participant)
    elif event_type == "participant_connected":
        await handle_participant_connected(call_id, room, participant)
    elif event_type == "participant_disconnected":
        await handle_participant_disconnected(call_id, room, participant)
    elif event_type == "room_finished":
        await handle_room_finished(call_id, room)
    elif event_type == "recording_started":
        await handle_recording_started(call_id, room, data)
    elif event_type == "recording_finished":
        await handle_recording_finished(call_id, room, data)

    return JSONResponse(content={"status": "ok"})


async def handle_room_started(call_id: str, room: dict, participant: dict):
    """Room started - initialize call tracking."""
    console.print(f"  [green]▶ Room started[/green]")
    # update_call_state's 3rd arg is a disposition string, not a metadata dict.
    state.update_call_state(call_id, "active")


async def handle_participant_connected(call_id: str, room: dict, participant: dict):
    """Participant connected - agent joined the room."""
    identity = participant.get("identity", "")
    if "agent" in identity.lower() or "assistant" in identity.lower():
        console.print(f"  [blue]🤖 Agent joined[/blue]")
    else:
        console.print(f"  [cyan]👤 Customer joined[/cyan]")
        # Track customer phone number from attributes
        attrs = participant.get("attributes", {})
        if "phone_number" in attrs:
            console.print(f"  📞 Phone: {attrs['phone_number']}")


async def handle_participant_disconnected(call_id: str, room: dict, participant: dict):
    """Participant disconnected - check if call should end."""
    identity = participant.get("identity", "")
    console.print(f"  [dim]👋 {identity} disconnected[/dim]")


async def handle_room_finished(call_id: str, room: dict):
    """Room finished - complete the call."""
    console.print(f"  [magenta]🏁 Room finished[/magenta]")
    # Trigger post-call processing
    await process_post_call(call_id)


async def handle_recording_started(call_id: str, room: dict, data: dict):
    """Recording started - track recording."""
    console.print(f"  [yellow]⏺  Recording started[/yellow]")
    state.update_call_state(call_id, "recording")


async def handle_recording_finished(call_id: str, room: dict, data: dict):
    """Recording finished - save recording URL."""
    recordings = data.get("recording", {})
    recording_url = recordings.get("url", "")
    console.print(f"  [green]⏹  Recording saved: {recording_url}[/green]")


async def process_post_call(call_id: str):
    """Post-call processing: summary, notification, cleanup."""
    console.print(f"\n  [bold]📋 Post-call processing for {call_id}[/bold]")

    # 1. Get call transcript from DynamoDB
    # 2. Generate summary via Qwen3.6
    # 3. Save to S3
    # 4. Publish SNS notification
    # 5. Update disposition

    console.print("  [dim]Post-call processing complete[/dim]")


if __name__ == "__main__":
    import uvicorn
    console.print(f"\n[bold cyan]📡 Webhook server starting on port {settings.AGENT_PORT}[/bold cyan]")
    uvicorn.run(app, host="0.0.0.0", port=settings.AGENT_PORT)
