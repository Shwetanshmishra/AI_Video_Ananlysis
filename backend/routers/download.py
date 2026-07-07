import logging

from fastapi import APIRouter, HTTPException

from models.schemas import DownloadRequest, DownloadResponse
from services import audio_service, registry
from services.audio_service import DownloadError

logger = logging.getLogger("router.download")
router = APIRouter(prefix="/download", tags=["download"])


@router.post("", response_model=DownloadResponse)
def download_audio(payload: DownloadRequest):
    if not payload.youtube_url or not payload.youtube_url.strip():
        raise HTTPException(status_code=422, detail="youtube_url must not be empty.")

    try:
        wav_path = audio_service.download_youtube_audio(payload.youtube_url.strip())
    except DownloadError as e:
        logger.error("Download failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Unexpected error during download")
        raise HTTPException(status_code=500, detail=f"Unexpected download error: {e}")

    duration = None
    try:
        duration = audio_service.get_duration_seconds(wav_path)
    except Exception:  # noqa: BLE001
        pass

    file_id = registry.register_file(wav_path, meta={"source": "youtube", "url": payload.youtube_url})

    return DownloadResponse(file_id=file_id, wav_path=wav_path, duration_seconds=duration)
