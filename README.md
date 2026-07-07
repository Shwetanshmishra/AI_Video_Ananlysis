# AI Video Assistant — FastAPI + Streamlit Architecture

This is the refactored two-service version of the AI Video Assistant.
All AI/ML logic (yt-dlp, audio chunking, Faster-Whisper, Sarvam AI,
LangChain, ChromaDB, Mistral AI, RAG) is unchanged — it has only been
*relocated* from the Streamlit app into a FastAPI backend. The Streamlit
app is now a pure UI that talks to the backend over HTTP.

```
project/
├── backend/                  # FastAPI service — does ALL the work
│   ├── app.py                 # FastAPI entrypoint, CORS, routers
│   ├── config.py               # env vars / paths
│   ├── routers/
│   │   ├── analyze.py          # POST /analyze
│   │   ├── chat.py             # POST /chat, GET/DELETE chat history
│   │   └── sessions.py         # GET/DELETE /session/{id}
│   ├── services/
│   │   ├── audio_processor.py  # yt-dlp download, convert, chunk
│   │   ├── transcriber.py      # Faster-Whisper + Sarvam AI
│   │   ├── summarizer.py       # title + summary (Mistral)
│   │   ├── extractor.py        # takeaways / claims / questions (Mistral)
│   │   ├── vector_store.py     # ChromaDB build/load per session
│   │   └── rag_engine.py       # LangChain RAG chain + chat
│   ├── models/schemas.py       # Pydantic request/response models
│   ├── utils/session_store.py  # in-memory session -> rag_chain map
│   ├── requirements.txt
│   ├── packages.txt            # ffmpeg, nodejs (system deps)
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                  # Streamlit service — UI ONLY
│   ├── app.py                  # same UI/CSS as before, calls backend via requests
│   ├── requirements.txt        # streamlit + requests only (no ML deps!)
│   ├── Dockerfile
│   └── .env.example
│
└── docker-compose.yml
```

## What changed vs. the original monolith

- All processing (download/convert/chunk, transcription, title, summary,
  takeaways, claims, questions, ChromaDB indexing, RAG) now happens inside
  FastAPI's `/analyze` endpoint. The frontend no longer imports
  `core.*` / `utils.*` modules — it only calls `requests.post(...)`.
- A new `POST /chat` endpoint lets the frontend ask questions against a
  previously built RAG chain by `session_id`. The LangChain `Runnable`
  object itself never leaves the backend process (it can't be serialized
  to JSON) — it's kept in `backend/utils/session_store.py`, keyed by
  `session_id`, and the frontend only ever sees JSON.
- `vector_store.py`'s Chroma collection name is now namespaced per
  `session_id` instead of one fixed name, so concurrent users hitting the
  same backend don't overwrite each other's transcript embeddings — the
  original script was single-user/local and didn't need this.
- `transcriber.py`'s `st.cache_resource` (Streamlit-only) was replaced
  with a plain thread-safe lazy singleton, since the Whisper model now
  loads inside a FastAPI worker process, not a Streamlit script.
- The Streamlit sidebar's step-by-step pipeline status UI is preserved.
  Since FastAPI returns one JSON response for the whole pipeline (no
  server-sent events), each step is shown "active" while the request is
  in flight and flips to "done" together when the response arrives,
  rather than ticking off individually as before.

Nothing about the prompts, chunking sizes, models, or RAG logic was
changed — every system/human prompt, chunk size, `k` value, and model
name from the original `core/*` files is identical here.

## Running locally (without Docker)

1. Backend (run from the **project root**, not from inside `backend/`,
   since `backend/app.py` imports its routers as `backend.routers.*`):
   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   cp backend/.env.example backend/.env   # fill in MISTRAL_API_KEY / SARVAM_API_KEY
   uvicorn backend.app:app --reload --port 8000
   ```

2. Frontend (separate terminal):
   ```bash
   cd frontend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # BACKEND_URL=http://localhost:8000
   streamlit run app.py
   ```

3. Open the Streamlit URL it prints (usually http://localhost:8501).

## Running with Docker Compose

```bash
cp backend/.env.example backend/.env   # fill in your API keys
docker compose up --build
```

- Backend: http://localhost:8000 (docs at /docs)
- Frontend: http://localhost:8501

## API summary

- `POST /analyze` — form-data: `youtube_url` (str) OR `file` (upload),
  plus `language` (`english` | `hinglish`). Returns `session_id`, `title`,
  `summary`, `transcript`, `action_items`, `key_decisions`,
  `open_questions`.
- `POST /chat` — JSON: `{"session_id": "...", "question": "..."}`.
  Returns `{"session_id", "question", "answer"}`.
- `GET /chat/{session_id}/history` — full chat history for a session.
- `DELETE /chat/{session_id}/history` — clears chat history.
- `GET /session/{session_id}` — re-fetch a previous analysis result.
- `DELETE /session/{session_id}` — drop a session from memory.
- `GET /health` — liveness check.

All endpoints return JSON error bodies of the shape
`{"detail": "..."}` with appropriate HTTP status codes (400 for bad
input, 404 for unknown session, 422 for empty transcription, 502 for
known upstream failures like yt-dlp/Sarvam, 500 for unexpected errors).

## Production note on session storage

`session_store.py` keeps sessions (including the live LangChain RAG
chain) in an in-memory dict inside a single backend process. This is
fine for one `uvicorn` worker. If you scale to multiple workers/replicas,
either pin a user's requests to one worker (sticky sessions) or move to
a shared store and rebuild the chain per-request via
`rag_engine.load_chain(session_id)` — the ChromaDB collection itself is
already persisted to disk per `session_id`, so only the chain wiring
needs reconstruction.
