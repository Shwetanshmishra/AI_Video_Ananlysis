from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers import analyze, chat, sessions

app = FastAPI(
    title="AI Video Assistant API",
    description="Backend for transcription, summarization, extraction and RAG chat over video/audio content.",
    version="1.0.0",
)

# Streamlit frontend (and any other client) talks to this API over HTTP.
# Tighten allow_origins in production to the actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "AI Video Assistant API is running. See /docs for the API reference."}
