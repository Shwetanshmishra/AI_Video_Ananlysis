"""
Audio acquisition & preprocessing service.

Handles:
- YouTube download via yt-dlp with multi-client fallback (android/web/ios),
  retries, proxy/cookie support, and informative error surfaces.
- Local file -> WAV conversion (pydub/ffmpeg).
- Chunking long WAV files into fixed-length pieces for transcription.
"""
import logging
import os
import time
import uuid

import yt_dlp
from pydub import AudioSegment

from config import settings

logger = logging.getLogger("audio_service")

# Order matters: try most-reliable clients first, fall back on failure.
_CLIENT_FALLBACK_ORDER = [
    ["android", "web"],
    ["ios"],
    ["web"],
    ["tv_embedded"],
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36"
)


class DownloadError(Exception):
    """Raised when every fallback client fails to download the video."""


def _base_ydl_opts(client_list: list[str]) -> dict:
    output_path = os.path.join(settings.downloads_dir, "%(id)s.%(ext)s")

    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_path,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 30,
        "extractor_args": {"youtube": {"player_client": client_list}},
        "http_headers": {"User-Agent": _USER_AGENT},
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    if settings.yt_dlp_proxy:
        opts["proxy"] = settings.yt_dlp_proxy
    if settings.yt_dlp_cookies_file and os.path.exists(settings.yt_dlp_cookies_file):
        opts["cookiefile"] = settings.yt_dlp_cookies_file

    return opts


def download_youtube_audio(url: str, max_attempts_per_client: int = 2) -> str:
    """
    Download audio for a YouTube URL, trying multiple player clients in order
    until one succeeds. Returns the path to the resulting WAV file.
    """
    last_error: Exception | None = None

    for client_list in _CLIENT_FALLBACK_ORDER:
        opts = _base_ydl_opts(client_list)
        for attempt in range(1, max_attempts_per_client + 1):
            try:
                logger.info(
                    "Attempting download with client=%s attempt=%d url=%s",
                    client_list, attempt, url,
                )
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)

                base = os.path.splitext(filename)[0]
                wav_file = base + ".wav"

                if os.path.exists(wav_file):
                    logger.info("Download succeeded with client=%s", client_list)
                    return wav_file

                raise DownloadError("yt-dlp completed but no WAV file was produced.")

            except yt_dlp.utils.DownloadError as e:
                last_error = e
                msg = str(e)
                logger.warning("Client %s attempt %d failed: %s", client_list, attempt, msg)
                # 403 / "Sign in to confirm" are exactly the cases the client
                # fallback is designed to solve — move to the next client set
                # immediately rather than burning retries on the same one.
                if "403" in msg or "Sign in" in msg or "confirm" in msg.lower():
                    break
                time.sleep(1.5 * attempt)
            except Exception as e:  # noqa: BLE001
                last_error = e
                logger.warning("Client %s attempt %d unexpected error: %s", client_list, attempt, e)
                time.sleep(1.0)

    raise DownloadError(
        f"All download strategies failed for url={url!r}. Last error: {last_error}"
    )


def save_upload_to_wav(file_bytes: bytes, original_filename: str) -> str:
    """Persist an uploaded file to disk and convert it to a normalized WAV."""
    os.makedirs(settings.uploads_dir, exist_ok=True)
    suffix = os.path.splitext(original_filename)[1] or ".dat"
    raw_path = os.path.join(settings.uploads_dir, f"{uuid.uuid4().hex}{suffix}")

    with open(raw_path, "wb") as f:
        f.write(file_bytes)

    return convert_to_wav(raw_path)


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to a 16kHz mono WAV using pydub/ffmpeg."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list[str]:
    """Split a WAV file into fixed-length chunk files for transcription."""
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []
    base = os.path.splitext(os.path.basename(wav_path))[0]
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start: start + chunk_ms]
        chunk_path = os.path.join(settings.chunks_dir, f"{base}_chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks


def get_duration_seconds(wav_path: str) -> float:
    audio = AudioSegment.from_wav(wav_path)
    return len(audio) / 1000.0


def cleanup_file(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logger.warning("Failed to clean up %s: %s", path, e)
