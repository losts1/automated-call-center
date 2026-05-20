"""
Central configuration for the call center system.
All settings loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # -- LiveKit --
    LIVEKIT_URL: str = "http://localhost:7880"
    LIVEKIT_API_KEY: str = "devkey"
    LIVEKIT_API_SECRET: str = "secretkey"

    # -- ElevenLabs --
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_TTS_MODEL: str = "eleven_turbo_v2_5"
    ELEVENLABS_TTS_VOICE: str = "pNInz6obpgDQGcFmaJgB"
    ELEVENLABS_STT_MODEL: str = "scribe_v1"

    # -- Ollama (Local LLM) --
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "lawllm"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024

    # -- Twilio --
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_SIP_DOMAIN: str = ""

    # -- Agent Behavior --
    AGENT_NAME: str = "Legal Assistant"
    AGENT_GREETING: str = (
        "Hello, thank you for calling. I'm your legal assistant. "
        "How may I help you today?"
    )
    CALL_RECORDING_NOTICE: str = (
        "This call may be recorded for quality assurance purposes. "
        "Please continue to speak if you consent."
    )

    # -- Server --
    AGENT_PORT: int = 8000
    WEBHOOK_SECRET: str = "webhook-secret"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
