import logging

from fastapi import APIRouter, HTTPException

from models.schemas import (
    RagBuildRequest,
    RagBuildResponse,
    RagChatRequest,
    RagChatResponse,
)
from services import registry
from services.rag_service import build_rag_chain, ask_question

logger = logging.getLogger("router.rag")
router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/build", response_model=RagBuildResponse)
def rag_build(payload: RagBuildRequest):
    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript must not be empty.")

    session_id = registry.new_id()
    try:
        rag_chain = build_rag_chain(payload.transcript, session_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to build RAG chain")
        raise HTTPException(status_code=500, detail=f"Failed to build RAG index: {e}")

    registry.register_rag_session(rag_chain, session_id=session_id)

    return RagBuildResponse(session_id=session_id)


@router.post("/chat", response_model=RagChatResponse)
def rag_chat(payload: RagChatRequest):
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty.")

    session = registry.get_rag_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Unknown or expired session_id: {payload.session_id}")

    try:
        answer = ask_question(session["chain"], payload.question.strip())
    except Exception as e:  # noqa: BLE001
        logger.exception("RAG chat failed")
        raise HTTPException(status_code=500, detail=f"RAG chat failed: {e}")

    return RagChatResponse(answer=answer)
