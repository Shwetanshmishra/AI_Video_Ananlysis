from fastapi import APIRouter, HTTPException

from models.schemas import AnalyzeResponse
from utils.session_store import get_session, delete_session

router = APIRouter(tags=["sessions"])


@router.get("/session/{session_id}", response_model=AnalyzeResponse)
async def get_session_result(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return AnalyzeResponse(
        session_id=session_id,
        title=session["title"],
        summary=session["summary"],
        transcript=session["transcript"],
        action_items=session["action_items"],
        key_decisions=session["key_decisions"],
        open_questions=session["open_questions"],
    )


@router.delete("/session/{session_id}")
async def remove_session(session_id: str):
    if get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    delete_session(session_id)
    return {"session_id": session_id, "deleted": True}
