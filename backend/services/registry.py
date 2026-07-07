"""
Lightweight registry that tracks:
- file_id -> wav path (from /download or /upload)
- session_id -> rag chain (in-memory, process-local)

For a single-instance deployment this in-memory dict is sufficient. For multi-worker
deployments, swap this for Redis (the interface below is intentionally minimal so
that swap is a drop-in change).
"""
import time
import uuid
from threading import Lock
from typing import Optional, Any, Dict

_lock = Lock()

_files: Dict[str, Dict[str, Any]] = {}
_rag_sessions: Dict[str, Dict[str, Any]] = {}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


# ---- file registry (download / upload / transcribe) ----

def register_file(wav_path: str, meta: Optional[dict] = None) -> str:
    file_id = new_id()
    with _lock:
        _files[file_id] = {
            "wav_path": wav_path,
            "created_at": time.time(),
            "meta": meta or {},
        }
    return file_id


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _files.get(file_id)


def update_file(file_id: str, **kwargs) -> None:
    with _lock:
        if file_id in _files:
            _files[file_id].update(kwargs)


# ---- rag session registry ----

def register_rag_session(rag_chain: Any, session_id: Optional[str] = None) -> str:
    session_id = session_id or new_id()
    with _lock:
        _rag_sessions[session_id] = {
            "chain": rag_chain,
            "created_at": time.time(),
        }
    return session_id


def get_rag_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _rag_sessions.get(session_id)


def cleanup_expired(ttl_seconds: int) -> None:
    now = time.time()
    with _lock:
        expired_files = [k for k, v in _files.items() if now - v["created_at"] > ttl_seconds]
        for k in expired_files:
            _files.pop(k, None)
        expired_sessions = [k for k, v in _rag_sessions.items() if now - v["created_at"] > ttl_seconds]
        for k in expired_sessions:
            _rag_sessions.pop(k, None)
