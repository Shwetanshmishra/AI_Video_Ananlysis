"""
In-memory session store.

A `rag_chain` (LangChain Runnable wrapping a Chroma retriever + LLM) is a
live Python object that cannot be sent over HTTP or stored in a database
trivially. Since the frontend now only talks to FastAPI over REST, the
backend keeps each session's pipeline output AND its rag_chain in this
process-local dict, addressed by session_id. The frontend never sees the
chain itself — it only ever sends/receives JSON.

NOTE: this is a simple in-memory store suitable for a single backend
worker process. For multi-worker / multi-instance production deployments,
replace this with a shared store (Redis, a DB-backed cache, etc.) — the
ChromaDB collection itself is already persisted to disk per session_id in
services/vector_store.py, so only the LangChain Runnable wiring would need
to be rebuilt via `rag_engine.load_chain(session_id)` on another worker.
"""

import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}


def create_session(session_id: str, data: Dict[str, Any]) -> None:
    with _lock:
        _sessions[session_id] = data


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _sessions.get(session_id)


def update_session(session_id: str, **fields: Any) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id].update(fields)


def delete_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def session_exists(session_id: str) -> bool:
    with _lock:
        return session_id in _sessions
