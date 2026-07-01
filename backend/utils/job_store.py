"""
In-memory job store for background pipeline tasks.

Each job goes through these states:
  pending  -> running -> done
                      -> failed

The frontend polls GET /status/{job_id} until state is 'done' or 'failed',
then fetches GET /session/{job_id} for the full results.
"""

import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def create_job(job_id: str) -> None:
    with _lock:
        _jobs[job_id] = {
            "state": "pending",
            "step": "Queued",
            "error": None,
        }


def set_running(job_id: str, step: str) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["state"] = "running"
            _jobs[job_id]["step"] = step


def set_done(job_id: str) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["state"] = "done"
            _jobs[job_id]["step"] = "Complete"


def set_failed(job_id: str, error: str) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["state"] = "failed"
            _jobs[job_id]["error"] = error


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _jobs.get(job_id)


def delete_job(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)