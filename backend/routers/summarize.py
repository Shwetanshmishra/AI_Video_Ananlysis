import logging

from fastapi import APIRouter, HTTPException

from models.schemas import SummarizeRequest, SummarizeResponse
from services.summarizer_service import summarize, generate_title

logger = logging.getLogger("router.summarize")
router = APIRouter(prefix="/summarize", tags=["summarize"])


@router.post("", response_model=SummarizeResponse)
def summarize_transcript(payload: SummarizeRequest):
    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript must not be empty.")

    try:
        title = generate_title(payload.transcript)
        summary = summarize(payload.transcript)
    except Exception as e:  # noqa: BLE001
        logger.exception("Summarization failed")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {e}")

    return SummarizeResponse(title=title, summary=summary)
