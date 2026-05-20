"""
Local LLM client for lawllm running on Ollama.
Handles legal domain conversation intelligence.
"""

import json
import urllib.request
from typing import Optional
from config.settings import settings


class LLMClient:
    """Client for the local LLM via Ollama API."""

    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    def _request(self, endpoint: str, payload: dict, timeout: int = 60) -> dict:
        """Send a request to the Ollama API."""
        url = f"{self.base_url}/api/{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())

    def chat(self, messages: list[dict], temperature: Optional[float] = None) -> dict:
        """Send a chat completion request via Ollama."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        return self._request("chat", payload)

    def generate(self, prompt: str, system: str = "", stream: bool = False) -> dict:
        """Send a generation request."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        return self._request("generate", payload)

    def _extract_text(self, result: dict) -> str:
        """Extract text from chat or generate response."""
        if "message" in result and "content" in result["message"]:
            return result["message"]["content"]
        return result.get("response", "")

    def classify_intent(self, transcript: str) -> dict:
        """Classify the intent of a call transcript."""
        prompt = (
            "You are a call center intent classifier. Analyze the customer's statement and return ONLY "
            "valid JSON with these keys: intent (one of: complaint, inquiry, appointment, escalation, "
            "feedback, sales, support), confidence (0.0-1.0), urgency (low, medium, high).\n\n"
            f"Customer said: {transcript}\n\nJSON:"
        )
        result = self.generate(prompt)
        text = self._extract_text(result).strip()
        # Extract JSON from possible surrounding text
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"intent": "inquiry", "confidence": 0.5, "urgency": "low"}

    def detect_sentiment(self, transcript: str) -> dict:
        """Detect sentiment and emotional state."""
        prompt = (
            "You are a sentiment analyzer for customer calls. Return ONLY valid JSON with: "
            "sentiment (positive, neutral, negative), emotion (calm, frustrated, angry, confused, happy, urgent), "
            "confidence (0.0-1.0), escalation_risk (low, medium, high).\n\n"
            f"Customer said: {transcript}\n\nJSON:"
        )
        result = self.generate(prompt)
        text = self._extract_text(result).strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"sentiment": "neutral", "emotion": "calm", "confidence": 0.5, "escalation_risk": "low"}

    def generate_response(self, context: list[dict], user_message: str, system_override: Optional[str] = None) -> str:
        """Generate a response based on conversation context."""
        system = system_override or (
            "You are a professional legal assistant AI for a law firm call center. "
            "You help customers with legal questions, case status inquiries, "
            "appointment scheduling, and general legal information.\n\n"
            "Rules:\n"
            "- You are NOT a lawyer. Never give definitive legal advice.\n"
            "- Always recommend speaking with an attorney for specific legal matters.\n"
            "- Be empathetic and patient.\n"
            "- Ask clarifying questions when needed.\n"
            "- Keep responses conversational, 1-3 sentences max.\n"
            "- If the caller is upset, acknowledge their concern first.\n"
            "- For urgent matters, prioritize escalation to a human.\n"
            "- Use plain language, avoid legal jargon."
        )

        # Ollama chat API expects messages array
        messages = [{"role": "system", "content": system}]
        messages.extend(context)
        messages.append({"role": "user", "content": user_message})

        result = self.chat(messages)
        return self._extract_text(result)

    def summarize_call(self, transcript: list[dict]) -> dict:
        """Summarize a completed call."""
        prompt = (
            "Summarize this call transcript. Return ONLY valid JSON with:\n"
            "- summary: 2-3 sentence summary\n"
            "- disposition: resolved, callback_scheduled, escalated, referred, no_action\n"
            "- next_steps: list of 1-3 recommended follow-ups\n"
            "- customer_satisfaction: 1-5 score\n\n"
            f"Transcript:\n{json.dumps(transcript, indent=2)}\n\nJSON:"
        )
        result = self.generate(prompt)
        text = self._extract_text(result).strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"summary": "Call completed", "disposition": "resolved", "next_steps": [], "customer_satisfaction": 3}


# Backward compat alias
QwenLegalClient = LLMClient
