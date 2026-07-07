"""
Audio acquisition / conversion / chunking service.

YouTube bot-detection bypass strategy:
  1. Cookies (most reliable) — if YOUTUBE_COOKIES env var is set (base64-encoded
     cookies.txt content), yt-dlp uses your real logged-in YouTube session.
     This bypasses IP-level blocks on cloud servers.
  2. Client fallback chain — tries ios, android, tv_embedded in sequence.
     Works on residential/low-traffic IPs; may fail on heavily shared cloud IPs.
"""

import os
import base64
import tempfile
import yt_dlp
from pydub import AudioSegment

from config import DOWNLOAD_DIR

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Client chain to try in order — most bot-friendly first.
_CLIENT_CHAIN = [
    ["ios"],
    ["android"],
    ["tv_embedded"],
    ["ios", "android"],
    ["android", "web"],
]

_BASE_OPTS = {
    "format":           "bestaudio/best",
    "noplaylist":       True,
    "quiet":            True,
    "no_warnings":      True,
    "retries":          3,
    "fragment_retries": 3,
    "nocheckcertificate": True,
    "source_address":   "0.0.0.0",
    "postprocessors": [
        {
            "key":              "FFmpegExtractAudio",
            "preferredcodec":   "wav",
            "preferredquality": "192",
        }
    ],
}

_IOS_UA = (
    "com.google.ios.youtube/19.29.1 "
    "(iPhone16,2; U; CPU iPhone OS 17_5_1 like Mac OS X)"
)
_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36"
)

_BOT_PHRASES = [
    "Sign in to confirm",
    "bot",
    "blocked",
    "This video is not available",
    "Precondition check failed",
    "Requested format is not available",
    "format is not available",
]


def _get_cookie_file() -> str | None:
    """
    If YOUTUBE_COOKIES env var is set (base64-encoded cookies.txt content),
    write it to a temp file and return the path. Returns None if not set.
    """
    cookies_b64 = os.getenv("YOUTUBE_COOKIES", "").strip()
    if not cookies_b64:
        return None
    try:
        cookies_bytes = base64.b64decode(cookies_b64)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".txt", prefix="yt_cookies_"
        )
        tmp.write(cookies_bytes)
        tmp.flush()
        tmp.close()
        print("  [yt-dlp] Using YouTube cookies from YOUTUBE_COOKIES env var")
        return tmp.name
    except Exception as e:
        print(f"  [yt-dlp] WARNING: Failed to decode YOUTUBE_COOKIES: {e}")
        return None


def _ydl_opts_for_client(
    client: list,
    output_path: str,
    use_ios_ua: bool,
    cookie_file: str | None,
) -> dict:
    opts = dict(_BASE_OPTS)
    opts["outtmpl"] = output_path
    opts["extractor_args"] = {"youtube": {"player_client": client}}
    opts["http_headers"] = {"User-Agent": _IOS_UA if use_ios_ua else _WEB_UA}
    if cookie_file:
        opts["cookiefile"] = cookie_file
    return opts


def download_youtube_audio(url: str) -> str:
    """
    Try cookies first (if available), then fall back through the client chain.
    Returns path to downloaded WAV on success. Raises RuntimeError if all fail.
    """
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    cookie_file = _get_cookie_file()
    last_error: Exception | None = None

    try:
        for attempt, client in enumerate(_CLIENT_CHAIN, start=1):
            use_ios_ua = any(c in ("ios", "tv_embedded") for c in client)
            opts = _ydl_opts_for_client(client, output_path, use_ios_ua, cookie_file)

            print(f"  [yt-dlp attempt {attempt}/{len(_CLIENT_CHAIN)}] client={client}")

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)

                base = os.path.splitext(filename)[0]
                wav_file = base + ".wav"

                if os.path.exists(wav_file):
                    print(f"  [yt-dlp] Success with client={client}")
                    return wav_file

                raise FileNotFoundError("yt-dlp completed but WAV file was not created.")

            except yt_dlp.utils.DownloadError as e:
                err_str = str(e)
                print(f"  [yt-dlp] client={client} failed: {err_str[:120]}")
                last_error = e

                bot_blocked = any(phrase in err_str for phrase in _BOT_PHRASES)
                if not bot_blocked:
                    # Transient network error — no point trying other clients
                    raise RuntimeError(f"Failed to download YouTube audio: {e}") from e

                continue  # bot-blocked — try next client

            except Exception as e:
                raise RuntimeError(f"Unexpected YouTube download error: {e}") from e

    finally:
        # Always clean up the temp cookie file
        if cookie_file and os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
            except OSError:
                pass

    raise RuntimeError(
        f"YouTube blocked all download attempts (tried {len(_CLIENT_CHAIN)} clients). "
        f"Last error: {last_error}"
    )


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start: start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)
    return chunks


def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking Audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready - {len(chunks)} chunk(s) created.")
    return chunks