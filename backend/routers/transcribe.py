import logging

from fastapi import APIRouter, HTTPException

from models.schemas import TranscribeRequest, TranscribeResponse
from services import audio_service, registry
from services.transcriber_service import transcribe_all

logger = logging.getLogger("router.transcribe")
router = APIRouter(prefix="/transcribe", tags=["transcribe"])


@router.post("", response_model=TranscribeResponse)
def transcribe(payload: TranscribeRequest):
    file_record = registry.get_file(payload.file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail=f"Unknown file_id: {payload.file_id}")

    wav_path = file_record["wav_path"]
    chunk_paths: list[str] = []

    try:
        chunk_paths = audio_service.chunk_audio(wav_path)
        transcript = transcribe_all(chunk_paths, payload.language)
    except Exception as e:  # noqa: BLE001
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        # Temporary chunk cleanup — keep the original WAV (registry-tracked) but
        # remove the per-chunk slices we created just for this request.
        for p in chunk_paths:
            audio_service.cleanup_file(p)

    registry.update_file(payload.file_id, transcript=transcript)

    return TranscribeResponse(file_id=payload.file_id, transcript=transcript)
