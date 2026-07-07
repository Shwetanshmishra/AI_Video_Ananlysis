import logging

from fastapi import APIRouter, HTTPException

from models.schemas import ExtractRequest, ExtractResponse
from services.extractor_service import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)

logger = logging.getLogger("router.extract")
router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("", response_model=ExtractResponse)
def extract(payload: ExtractRequest):
    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript must not be empty.")

    try:
        action_items = extract_action_items(payload.transcript)
        key_decisions = extract_key_decisions(payload.transcript)
        open_questions = extract_questions(payload.transcript)
    except Exception as e:  # noqa: BLE001
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    return ExtractResponse(
        action_items=action_items,
        key_decisions=key_decisions,
        open_questions=open_questions,
    )
