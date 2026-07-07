"""
LiveKit Telephony Agent - handles inbound/outbound calls with:
- ElevenLabs STT (Scribe v2) for speech-to-text
- ElevenLabs TTS (Turbo v2.5) for text-to-speech
- Local lawllm via Ollama for conversation intelligence
- moto (local AWS mock) for call state & recording management
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from rich.console import Console

from config.settings import settings
from agent.llm_client import QwenLegalClient
from agent.state_manager import StateManager
from agent.recording_manager import RecordingManager

console = Console()

# -- System Prompts --
LEGAL_AGENT_PROMPT = """You are a professional legal assistant AI for a law firm.
Your role is to:
1. Answer basic legal questions (informational, not advice)
2. Schedule consultations/appointments
3. Take case details and route to appropriate attorney
4. Handle client inquiries about case status
5. Collect information for intake forms

Rules:
- You are NOT a lawyer. Never give definitive legal advice.
- Always recommend speaking with an attorney for specific legal matters.
- Be empathetic and patient.
- Ask clarifying questions to gather necessary information.
- Keep responses conversational, 1-3 sentences max.
- If the caller is upset, acknowledge their feelings first.
- For urgent/legal emergency situations, prioritize transfer to a human.

Current date: {date}
"""


class TelephonyAgent:
    """Main telephony agent handling call flow."""

    def __init__(self):
        self.llm = QwenLegalClient()
        self.state = StateManager()
        self.call_contexts: dict[str, list[dict]] = {}
        self.recording_urls: dict[str, str] = {}
        self.livekit_url = settings.LIVEKIT_URL
        self.livekit_api_key = settings.LIVEKIT_API_KEY
        self.livekit_api_secret = settings.LIVEKIT_API_SECRET

    async def handle_inbound_call(self, room_name: str, participant: dict) -> None:
        """Handle an incoming phone call via SIP trunk."""
        call_id = str(uuid.uuid4())[:8]
        phone_number = participant.get("attributes", {}).get("phone_number", "unknown")

        console.print(f"\n[bold blue]📞 INBOUND CALL[/bold blue] {phone_number}")
        console.print(f"   Call ID: {call_id}")
        console.print(f"   Room: {room_name}")

        # Create call record
        call_record = self.state.create_call_record(
            room_name, participant.get("identity", "unknown"), phone_number
        )
        self.call_contexts[call_record["call_id"]] = []

        # Play greeting + recording notice
        await self._play_greeting(call_record["call_id"], phone_number)

        # Start listening loop
        await self._conversation_loop(call_record["call_id"], room_name)

        # Complete call
        await self._complete_call(call_record["call_id"])

    async def _play_greeting(self, call_id: str, phone_number: str) -> None:
        """Play the initial greeting and recording notice."""
        greeting = (
            "Thank you for calling. I'm your legal assistant. How may I help you today? "
            + settings.CALL_RECORDING_NOTICE
        )

        self.call_contexts[call_id] = [
            {
                "role": "system",
                "content": LEGAL_AGENT_PROMPT.format(
                    date=datetime.now().strftime("%B %d, %Y")
                ),
            },
            {"role": "assistant", "content": greeting},
        ]
        console.print(f"[green]▶ Greeting played[/green]")

    async def _conversation_loop(self, call_id: str, room_name: str) -> None:
        """Main conversation loop: listen -> transcribe -> think -> respond."""
        max_turns = 50  # Safety limit
        turn = 0

        console.print("[yellow]🎙️  Listening for customer speech...[/yellow]")

        # In a real LiveKit integration, this would use the agents SDK:
        # from livekit.agents import AgentSession, llm, tts, stt
        # But we'll structure it here for clarity

        while turn < max_turns:
            turn += 1
            console.print(f"\n[bold]Turn {turn}[/bold]")

            # 1. LISTEN - In production, ElevenLabs STT streams audio to text
            customer_text = await self._listen_for_speech(call_id)
            if not customer_text:
                console.print("[red]⚠️  No speech detected, ending call[/red]")
                break

            console.print(f"[cyan]👤 Customer: {customer_text}[/cyan]")

            # 2. ANALYZE - Intent + Sentiment
            intent = {"intent": "inquiry", "confidence": 0.5, "urgency": "low"}
            sentiment = {
                "sentiment": "neutral",
                "emotion": "calm",
                "confidence": 0.5,
                "escalation_risk": "low",
            }

            try:
                intent = self.llm.classify_intent(customer_text)
                sentiment = self.llm.detect_sentiment(customer_text)

                console.print(
                    f"   🎯 Intent: {intent['intent']} "
                    f"(confidence: {intent['confidence']:.2f})"
                )
                console.print(
                    f"   😊 Sentiment: {sentiment['sentiment']} "
                    f"/ {sentiment['emotion']}"
                )
                console.print(
                    f"   ⚠️  Escalation risk: {sentiment['escalation_risk']}"
                )

                # Track in state
                self.state.add_transcript_entry(
                    call_id,
                    {
                        "role": "user",
                        "text": customer_text,
                        "source": "customer",
                        "metadata": json.dumps(
                            {"intent": intent, "sentiment": sentiment}
                        ),
                    },
                )
            except Exception as e:
                console.print(f"[red]Analysis error: {e}[/red]")
                self.state.add_transcript_entry(
                    call_id,
                    {
                        "role": "user",
                        "text": customer_text,
                        "source": "customer",
                    },
                )

            # 3. GENERATE RESPONSE
            context = self.call_contexts.get(call_id, [])
            try:
                # Build context with recent turns (last 6 messages)
                recent_context = context[-6:] if len(context) > 6 else context
                response = self.llm.generate_response(recent_context, customer_text)
            except Exception as e:
                console.print(f"[red]LLM error: {e}[/red]")
                response = (
                    "I'm sorry, I'm having trouble processing your request. "
                    "Let me connect you with a human representative."
                )

            console.print(f"[bold green]🤖 Agent: {response}[/bold green]")

            # 4. Add to context
            self.call_contexts[call_id].extend(
                [
                    {"role": "user", "content": customer_text},
                    {"role": "assistant", "content": response},
                ]
            )

            # 5. TTS - Play response (in production, streams to LiveKit)
            await self._speak_response(call_id, response)

            # 6. Check for escalation triggers
            if (
                sentiment.get("escalation_risk") == "high"
                or intent.get("intent") == "escalation"
            ):
                console.print(
                    "[red bold]⚠️  HIGH ESCALATION RISK - flagging for human transfer[/red]"
                )

        console.print(
            f"\n[yellow]Conversation ended after {turn} turns[/yellow]"
        )

    async def _listen_for_speech(self, call_id: str) -> Optional[str]:
        """
        In production: Uses ElevenLabs STT (Scribe v2) via LiveKit agents SDK.
        Streams audio from LiveKit room -> transcribes to text.

        For now, returns a mock for development/testing.
        """
        # Production code (uncomment when LiveKit is set up):
        # from livekit.agents import stt
        # from livekit.plugins.elevenlabs import STT
        #
        # stt_instance = STT(
        #     model=settings.ELEVENLABS_STT_MODEL,
        #     language="en",
        #     vad_enabled=True,
        #     vad_agency=0.5,
        #     vad_threshold=0.6,
        # )
        # # ... stream room audio to STT ...

        # MOCK for development - replace with real LiveKit integration
        await asyncio.sleep(1)  # Simulate VAD detection delay
        return None  # Returns None to signal end in this mock mode

    async def _speak_response(self, call_id: str, text: str) -> None:
        """
        In production: Uses ElevenLabs TTS (Turbo v2.5) via LiveKit agents SDK.
        Streams audio back to the LiveKit room.

        For now, just logs the response.
        """
        # Production code:
        # from livekit.agents import tts
        # from livekit.plugins.elevenlabs import TTS
        #
        # tts_instance = TTS(
        #     model=settings.ELEVENLABS_TTS_MODEL,
        #     voice_id=settings.ELEVENLABS_TTS_VOICE,
        # )
        # async for audio in tts_instance.stream(text):
        #     await room.local_participant.publish_track(audio, media_track=audio)

        console.print(f"   [dim]🔊 TTS: '{text[:60]}...[/dim]")

    async def _complete_call(self, call_id: str) -> None:
        """Complete the call: summarize, save, notify."""
        console.print(f"\n[bold magenta]📋 Completing call {call_id}[/bold magenta]")

        context = self.call_contexts.pop(call_id, [])

        # Generate call summary
        try:
            summary = self.llm.summarize_call(context)
            console.print(f"   📝 Summary: {summary['summary']}")
            console.print(f"   ✅ Disposition: {summary['disposition']}")
            console.print(
                f"   ⭐ Satisfaction: {summary['customer_satisfaction']}/5"
            )
            console.print(
                f"   📋 Next steps: {', '.join(summary['next_steps'])}"
            )
        except Exception as e:
            console.print(f"[red]Summary error: {e}[/red]")
            summary = {
                "summary": "Call completed",
                "disposition": "resolved",
                "next_steps": [],
                "customer_satisfaction": 3,
            }

        # Update state
        self.state.complete_call(call_id, summary["disposition"], summary)

        console.print("[green]✅ Call completed and saved[/green]")


async def run_agent():
    """Main entry point for the telephony agent."""
    console.print(
        "[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]"
    )
    console.print(
        "[bold cyan]║     Legal Call Center Agent Starting     ║[/bold cyan]"
    )
    console.print(
        "[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]"
    )

    agent = TelephonyAgent()

    # Check LLM connectivity (LLMClient methods are synchronous)
    try:
        result = agent.llm.chat(
            [{"role": "user", "content": "Hello"}], temperature=0.1
        )
        console.print(
            f"[green]✅ LLM connected: {agent.llm.model}[/green]"
        )
    except Exception as e:
        console.print(f"[red]❌ LLM connection failed: {e}[/red]")
        console.print("   Make sure Ollama is running on localhost:11434")

    console.print(
        "\n[bold]Agent ready. Waiting for LiveKit SIP connections...[/bold]"
    )
    console.print(
        "[dim]Configure your SIP trunk to route calls to the LiveKit server[/dim]"
    )


if __name__ == "__main__":
    asyncio.run(run_agent())
