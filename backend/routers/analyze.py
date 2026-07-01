import os
import uuid
import shutil
import traceback
import threading

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from config import UPLOAD_DIR
from utils.session_store import create_session
from utils.job_store import create_job, set_running, set_done, set_failed, get_job

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


# ── Response models ──────────────────────────────────────────────────────────

class SubmitResponse(BaseModel):
    job_id: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    state: str        # pending | running | done | failed
    step: str         # human-readable current step label
    error: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

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


# ── Background pipeline ───────────────────────────────────────────────────────

def _run_pipeline(job_id: str, source: str, language: str, local_upload_path: str | None):
    """Runs the full pipeline in a background thread. Updates job_store at each step."""
    try:
        set_running(job_id, "Downloading / converting audio")
        chunks = process_input(source)

        set_running(job_id, "Transcribing audio")
        transcript = transcribe_all(chunks, language)
        if not transcript.strip():
            set_failed(job_id, "Transcription produced empty text.")
            return

        set_running(job_id, "Generating title")
        title = generate_title(transcript)

        set_running(job_id, "Summarizing transcript")
        summary = summarize(transcript)

        set_running(job_id, "Extracting insights")
        action_items = extract_action_items(transcript)
        decisions    = extract_key_decisions(transcript)
        questions    = extract_questions(transcript)

        set_running(job_id, "Building RAG index")
        rag_chain = build_rag_chain(transcript, job_id)

        create_session(
            job_id,
            {
                "title":         title,
                "transcript":    transcript,
                "summary":       summary,
                "action_items":  action_items,
                "key_decisions": decisions,
                "open_questions":questions,
                "rag_chain":     rag_chain,
                "chat_history":  [],
            },
        )
        set_done(job_id)

    except Exception as e:
        traceback.print_exc()
        err = str(e)
        if any(p in err for p in ["Sign in to confirm", "bot", "blocked all download"]):
            err = (
                "YouTube blocked the download (anti-bot protection). "
                "Please download the video and upload the file instead."
            )
        set_failed(job_id, err)

    finally:
        if local_upload_path and os.path.exists(local_upload_path):
            try:
                os.remove(local_upload_path)
            except OSError:
                pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=SubmitResponse)
async def analyze(
    youtube_url: str | None = Form(default=None),
    language: str = Form(default="english"),
    file: UploadFile | None = File(default=None),
):
    """
    Submit a video for analysis. Returns immediately with a job_id.
    Poll GET /status/{job_id} to track progress.
    When state == 'done', results are available at GET /session/{job_id}.
    """
    if not youtube_url and not file:
        raise HTTPException(status_code=400, detail="Provide either 'youtube_url' or an uploaded 'file'.")
    if youtube_url and file:
        raise HTTPException(status_code=400, detail="Provide only one of 'youtube_url' or 'file', not both.")

    language = (language or "english").strip().lower()
    if language not in {"english", "hinglish"}:
        raise HTTPException(status_code=400, detail="language must be 'english' or 'hinglish'.")

    local_upload_path: str | None = None
    if file is not None:
        local_upload_path = _save_upload(file)
        source = local_upload_path
    else:
        source = youtube_url.strip()

    job_id = uuid.uuid4().hex
    create_job(job_id)

    # Fire pipeline in a background thread so this endpoint returns immediately
    t = threading.Thread(
        target=_run_pipeline,
        args=(job_id, source, language, local_upload_path),
        daemon=True,
    )
    t.start()

    return SubmitResponse(job_id=job_id, message="Pipeline started. Poll /status/{job_id} for progress.")


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Poll this endpoint every few seconds to track pipeline progress."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return StatusResponse(
        job_id=job_id,
        state=job["state"],
        step=job["step"],
        error=job.get("error"),
    )