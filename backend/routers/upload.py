import logging
import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from config import settings
from models.schemas import DownloadResponse
from services import audio_service, registry

logger = logging.getLogger("router.upload")
router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".m4a"}


@router.post("", response_model=DownloadResponse)
async def upload_file(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {suffix}")

    raw_path = os.path.join(settings.uploads_dir, f"{uuid.uuid4().hex}{suffix}")

    try:
        # Stream the upload to disk in chunks rather than reading it all into memory.
        with open(raw_path, "wb") as out_file:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB
                if not chunk:
                    break
                out_file.write(chunk)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to save upload")
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
    finally:
        await file.close()

    try:
        wav_path = audio_service.convert_to_wav(raw_path)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to convert upload to WAV")
        raise HTTPException(status_code=500, detail=f"Failed to convert upload: {e}")
    finally:
        audio_service.cleanup_file(raw_path)

    duration = None
    try:
        duration = audio_service.get_duration_seconds(wav_path)
    except Exception:  # noqa: BLE001
        pass

    file_id = registry.register_file(wav_path, meta={"source": "upload", "filename": file.filename})

    return DownloadResponse(file_id=file_id, wav_path=wav_path, duration_seconds=duration)
