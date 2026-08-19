"""Voice API endpoints for speech transcription and text-to-speech generation."""

import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

try:
    from mcp_server.tools.voice_tools import transcribe_audio, speak_text
except ImportError:
    try:
        from tools.voice_tools import transcribe_audio, speak_text  # type: ignore[import-not-found]
    except ImportError:
        transcribe_audio = None
        speak_text = None

router = APIRouter(prefix="/api/voice", tags=["Voice"])


class TranscribeRequest(BaseModel):
    audio_base64: str
    language: Optional[str] = "en"
    model: Optional[str] = "whisper-base"


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0


@router.post("/transcribe")
async def handle_transcribe(req: TranscribeRequest):
    """Transcribe audio sent as base64 string."""
    if transcribe_audio is None:
        raise HTTPException(status_code=500, detail="Voice tools not available")
    res = transcribe_audio(audio_base64=req.audio_base64, language=req.language or "en", model=req.model or "whisper-base")
    return res


@router.post("/speak")
async def handle_speak(req: SpeakRequest):
    """Generate speech parameters from text."""
    if speak_text is None:
        raise HTTPException(status_code=500, detail="Voice tools not available")
    res = speak_text(text=req.text, voice=req.voice or "default", speed=req.speed or 1.0)
    return res
