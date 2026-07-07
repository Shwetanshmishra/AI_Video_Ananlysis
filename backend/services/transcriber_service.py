"""
Transcription service. Faster-Whisper model is loaded exactly once per process
via lru_cache and reused across all requests.
"""
import logging
import os
from functools import lru_cache

import requests
from faster_whisper import WhisperModel
from pydub import AudioSegment

from config import settings

logger = logging.getLogger("transcriber")


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    logger.info(
        "Loading faster-whisper model=%s device=%s compute_type=%s (one-time load)",
        settings.whisper_model, settings.whisper_device, settings.whisper_compute_type,
    )
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_chunk_whisper(chunk_path: str) -> str:
    model = get_whisper_model()
    segments, _info = model.transcribe(chunk_path, task="transcribe")
    return "".join(segment.text for segment in segments).strip()


def _send_to_sarvam(piece_path: str) -> str:
    if not settings.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    headers = {"api-subscription-key": settings.sarvam_api_key}
    with open(piece_path, "rb") as f:
        files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
        data = {"model": settings.sarvam_stt_model, "with_diarization": "false"}
        response = requests.post(
            settings.sarvam_stt_translate_url,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        logger.error("Sarvam returned %s: %s", response.status_code, response.text)
        response.raise_for_status()

    return response.json().get("transcript", "")


def transcribe_chunk_sarvam(chunk_path: str) -> str:
    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = settings.sarvam_piece_seconds * 1000

    full_text = ""
    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")
        try:
            full_text += _send_to_sarvam(piece_path) + " "
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    return full_text.strip()


def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)
    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list[str], language: str = "english") -> str:
    full_transcript = ""
    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    logger.info("Transcribing %d chunk(s) using %s", len(chunks), engine)

    for i, chunk in enumerate(chunks):
        logger.info("Transcribing chunk %d/%d", i + 1, len(chunks))
        text = transcribe_chunk(chunk, language=language)
        full_transcript += text + " "

    return full_transcript.strip()
