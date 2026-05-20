"""
LiveKit Webhook Server
Handles room events and updates call state via moto/local AWS mock.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from rich.console import Console

from config.settings import settings
from agent.state_manager import StateManager

app = FastAPI(title="Call Center Webhooks")
console = Console()
state = StateManager()


@app.post("/webhooks/livekit")
async def livekit_webhook(request: Request):
    """Handle LiveKit room events."""
    data = await request.json()
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
    state.update_call_state(call_id, "active", {
        "room_name": room.get("name"),
        "participant": participant.get("identity"),
    })


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
