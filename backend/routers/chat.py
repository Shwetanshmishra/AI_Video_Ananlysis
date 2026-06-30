import traceback

from fastapi import APIRouter, HTTPException

from backend.models.schemas import ChatRequest, ChatResponse, ChatHistoryResponse, ChatHistoryItem
from backend.utils.session_store import get_session, update_session
from backend.services.rag_engine import ask_question

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    session = get_session(payload.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{payload.session_id}' not found. Run /analyze first.",
        )

    rag_chain = session.get("rag_chain")
    if rag_chain is None:
        raise HTTPException(status_code=500, detail="Session has no RAG chain available.")

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty.")

    try:
        answer = ask_question(rag_chain, question)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}") from e

    history = session.get("chat_history", [])
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    update_session(payload.session_id, chat_history=history)

    return ChatResponse(session_id=payload.session_id, question=question, answer=answer)


@router.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def chat_history(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    history = [ChatHistoryItem(**item) for item in session.get("chat_history", [])]
    return ChatHistoryResponse(session_id=session_id, history=history)


@router.delete("/chat/{session_id}/history")
async def clear_chat_history(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    update_session(session_id, chat_history=[])
    return {"session_id": session_id, "cleared": True}
