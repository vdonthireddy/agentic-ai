"""Tests for voice interface tools and gateway endpoints."""

import pytest
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.voice_tools import transcribe_audio, speak_text


class TestVoiceTools:
    def test_transcribe_empty_audio(self):
        result = transcribe_audio(audio_base64="")
        assert result["status"] == "error"
        assert "No audio" in result["message"]

    def test_transcribe_valid_base64(self):
        sample_bytes = b"RIFF....WAVEfmt ...."
        b64 = base64.b64encode(sample_bytes).decode("utf-8")
        result = transcribe_audio(audio_base64=b64, language="en")
        assert result["status"] == "success"
        assert "transcription" in result

    def test_speak_text_basic(self):
        result = speak_text(text="Hello world, welcome to Agentic AI.")
        assert result["status"] == "success"
        assert result["voice"] == "default"
        assert result["speed"] == 1.0
        assert "Speech generated" in result["message"]

    def test_speak_text_empty(self):
        result = speak_text(text="")
        assert result["status"] == "error"

    def test_speak_text_custom_voice_and_speed(self):
        result = speak_text(text="Test speech", voice="nova", speed=1.2)
        assert result["status"] == "success"
        assert result["voice"] == "nova"
        assert result["speed"] == 1.2
