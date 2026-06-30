from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    session_id: str
    title: str
    summary: str
    transcript: str
    action_items: str
    key_decisions: str
    open_questions: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Session id returned by /analyze")
    question: str = Field(..., min_length=1, description="Question about the transcript")


class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    history: List[ChatHistoryItem]


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
