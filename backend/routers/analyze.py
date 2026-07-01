import os
import uuid
import shutil
import tempfile
import traceback

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from config import UPLOAD_DIR
from models.schemas import AnalyzeResponse
from utils.session_store import create_session

from services.audio_processor import process_input
from services.transcriber import transcribe_all
from services.summarizer import summarize, generate_title
from services.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from services.rag_engine import build_rag_chain

router = APIRouter(tags=["analyze"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav"}


def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{suffix}")

    try:
        with open(dest_path, "wb") as out_file:
            shutil.copyfileobj(upload.file, out_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}") from e
    finally:
        upload.file.close()

    return dest_path


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    youtube_url: str | None = Form(default=None),
    language: str = Form(default="english"),
    file: UploadFile | None = File(default=None),
):
    """
    Run the full pipeline (download/convert -> chunk -> transcribe ->
    title -> summary -> action items -> key decisions -> questions -> RAG
    index) on either an uploaded file or a YouTube URL, and return all
    results plus a session_id that /chat can use afterwards.
    """
    if not youtube_url and not file:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'youtube_url' or an uploaded 'file'.",
        )
    if youtube_url and file:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of 'youtube_url' or 'file', not both.",
        )

    language = (language or "english").strip().lower()
    if language not in {"english", "hinglish"}:
        raise HTTPException(status_code=400, detail="language must be 'english' or 'hinglish'.")

    source: str
    local_upload_path: str | None = None

    if file is not None:
        local_upload_path = _save_upload(file)
        source = local_upload_path
    else:
        source = youtube_url.strip()

    session_id = uuid.uuid4().hex

    try:
        chunks = process_input(source)

        transcript = transcribe_all(chunks, language)
        if not transcript.strip():
            raise HTTPException(status_code=422, detail="Transcription produced empty text.")

        title = generate_title(transcript)
        summary = summarize(transcript)

        action_items = extract_action_items(transcript)
        decisions = extract_key_decisions(transcript)
        questions = extract_questions(transcript)

        rag_chain = build_rag_chain(transcript, session_id)

        create_session(
            session_id,
            {
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
                "rag_chain": rag_chain,
                "chat_history": [],
            },
        )

        return AnalyzeResponse(
            session_id=session_id,
            title=title,
            summary=summary,
            transcript=transcript,
            action_items=action_items,
            key_decisions=decisions,
            open_questions=questions,
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        err = str(e)
        # Give a user-friendly message for YouTube bot-detection blocks
        if any(phrase in err for phrase in ["Sign in to confirm", "bot", "blocked all download"]):
            raise HTTPException(
                status_code=502,
                detail=(
                    "YouTube blocked the download (anti-bot protection triggered on all "
                    "available clients). Please download the video manually and upload "
                    "the file instead — the upload path works 100% reliably."
                ),
            ) from e
        raise HTTPException(status_code=502, detail=err) from e
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}") from e
    finally:
        if local_upload_path and os.path.exists(local_upload_path):
            try:
                os.remove(local_upload_path)
            except OSError:
                pass
