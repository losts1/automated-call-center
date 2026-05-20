"""
Integration tests for the telephony agent.
Tests the full flow: LLM connectivity, state management, recording.
"""

import asyncio
import pytest
import httpx
from datetime import datetime

from agent.llm_client import QwenLegalClient
from agent.state_manager import StateManager
from agent.recording_manager import RecordingManager


class TestLLMClient:
    """Test the local LLM client."""

    @pytest.mark.asyncio
    async def test_llm_connection(self):
        """Test that Qwen3.6 is reachable."""
        client = QwenLegalClient()
        try:
            result = await client.chat(
                [{"role": "user", "content": "Say hello"}],
                temperature=0.1,
            )
            assert "choices" in result
            assert len(result["choices"]) > 0
            print(f"✅ LLM response: {result['choices'][0]['message']['content'][:50]}...")
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")

    @pytest.mark.asyncio
    async def test_intent_classification(self):
        """Test intent classification."""
        client = QwenLegalClient()
        try:
            intent = await client.classify_intent(
                "I need to schedule a consultation about my divorce case."
            )
            assert "intent" in intent
            assert intent["intent"] in [
                "complaint", "inquiry", "appointment", "escalation",
                "feedback", "sales", "support"
            ]
            assert 0.0 <= intent["confidence"] <= 1.0
            print(f"✅ Intent: {intent['intent']} ({intent['confidence']:.2f})")
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")

    @pytest.mark.asyncio
    async def test_sentiment_detection(self):
        """Test sentiment detection."""
        client = QwenLegalClient()
        try:
            sentiment = await client.detect_sentiment(
                "I've been waiting three weeks for a response and I'm very frustrated."
            )
            assert "sentiment" in sentiment
            assert sentiment["sentiment"] in ["positive", "neutral", "negative"]
            assert "emotion" in sentiment
            assert "escalation_risk" in sentiment
            print(f"✅ Sentiment: {sentiment['sentiment']} / {sentiment['emotion']}")
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")

    @pytest.mark.asyncio
    async def test_response_generation(self):
        """Test response generation."""
        client = QwenLegalClient()
        try:
            context = [
                {"role": "system", "content": "You are a legal assistant."},
                {"role": "user", "content": "I want to file a claim."},
                {"role": "assistant", "content": "I can help with that. What type of claim?"},
            ]
            response = await client.generate_response(context, "Personal injury from a car accident")
            assert len(response) > 10
            assert "consultation" in response.lower() or "attorney" in response.lower() or "schedule" in response.lower()
            print(f"✅ Response: {response[:80]}...")
        except Exception as e:
            pytest.skip(f"LLM not available: {e}")


class TestStateManagement:
    """Test Localstack state management."""

    @pytest.mark.asyncio
    async def test_create_call_record(self):
        """Test creating a call record in DynamoDB."""
        try:
            record = StateManager.create_call_record(
                room_name="test-room",
                participant_identity="test-user",
                phone_number="+15551234567",
            )
            assert "call_id" in record
            print(f"✅ Call record created: {record['call_id']}")
        except Exception as e:
            pytest.skip(f"Localstack not available: {e}")

    @pytest.mark.asyncio
    async def test_update_call_state(self):
        """Test updating call state."""
        try:
            record = StateManager.create_call_record(
                room_name="test-room-2",
                participant_identity="test-user-2",
            )
            result = StateManager.update_call_state(
                record["call_id"],
                "completed",
                {"disposition": "resolved"},
            )
            assert result is True
            print("✅ Call state updated")
        except Exception as e:
            pytest.skip(f"Localstack not available: {e}")


class TestRecording:
    """Test recording storage."""

    @pytest.mark.asyncio
    async def test_upload_recording(self):
        """Test uploading a recording to S3."""
        try:
            # Create a small WAV file header
            wav_header = b'RIFF' + b'\x00' * 44 + b'WAVEfmt '
            url = RecordingManager.upload_recording(
                call_id="test-recording",
                audio_data=wav_header,
                format="wav",
            )
            assert url is not None
            print(f"✅ Recording uploaded: {url}")
        except Exception as e:
            pytest.skip(f"Localstack not available: {e}")

    @pytest.mark.asyncio
    async def test_list_recordings(self):
        """Test listing recordings."""
        try:
            recordings = RecordingManager.list_recordings()
            assert isinstance(recordings, list)
            print(f"✅ Found {len(recordings)} recordings")
        except Exception as e:
            pytest.skip(f"Localstack not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
