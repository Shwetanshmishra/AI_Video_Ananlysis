"""
Audio acquisition / conversion / chunking service.

YouTube bot-detection bypass strategy:
  yt-dlp supports multiple "player clients" — each mimics a different
  YouTube client (iOS app, Android app, TV browser, web browser).
  YouTube's bot detection is much stricter on web/desktop clients than on
  mobile app clients. We try clients in order from least-detected to most:

    1. ios        – YouTube iOS app; least scrutinised, works most often
    2. android    – YouTube Android app; also lightly checked
    3. tv_embedded – YouTube TV/embedded; often bypasses age/bot checks
    4. web        – Standard web browser; most likely to be blocked

  If ALL clients fail, we raise a clear RuntimeError that the router
  translates into a user-friendly 502 message.
"""

from pydub import AudioSegment
import os
import yt_dlp

from config import DOWNLOAD_DIR

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Client chain to try in order — most bot-friendly first.
# Each entry is a list passed to yt-dlp's player_client extractor arg.
_CLIENT_CHAIN = [
    ["ios"],
    ["android"],
    ["tv_embedded"],
    ["ios", "android"],       # combined fallback
    ["android", "web"],       # original behaviour as last resort
]

# Common base options shared across all attempts
_BASE_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "retries": 3,                 # fewer retries per attempt — we retry at client level
    "fragment_retries": 3,
    "nocheckcertificate": True,
    "source_address": "0.0.0.0",
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }
    ],
}

# iOS User-Agent (what real iPhone YouTube app sends)
_IOS_UA = (
    "com.google.ios.youtube/19.29.1 "
    "(iPhone16,2; U; CPU iPhone OS 17_5_1 like Mac OS X)"
)

# Standard web UA as fallback
_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36"
)


def _ydl_opts_for_client(client: list, output_path: str, use_ios_ua: bool) -> dict:
    opts = dict(_BASE_OPTS)
    opts["outtmpl"] = output_path
    opts["extractor_args"] = {"youtube": {"player_client": client}}
    opts["http_headers"] = {"User-Agent": _IOS_UA if use_ios_ua else _WEB_UA}
    return opts


def download_youtube_audio(url: str) -> str:
    """
    Try each client in _CLIENT_CHAIN in order.
    Returns the path to the downloaded WAV on first success.
    Raises RuntimeError if all clients fail.
    """
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    last_error: Exception | None = None

    for attempt, client in enumerate(_CLIENT_CHAIN, start=1):
        # Use iOS UA for iOS/TV clients, web UA for web/android
        use_ios_ua = any(c in ("ios", "tv_embedded") for c in client)

        opts = _ydl_opts_for_client(client, output_path, use_ios_ua)

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

            # If it's a hard block (not a transient network error), try next client
            # immediately without hammering retries.
            bot_blocked = any(
                phrase in err_str
                for phrase in [
                    "Sign in to confirm",
                    "bot",
                    "blocked",
                    "This video is not available",
                    "Precondition check failed",
                ]
            )
            if not bot_blocked:
                # Transient error (DNS, timeout) — no point trying other clients
                raise RuntimeError(f"Failed to download YouTube audio: {e}") from e

            # Bot-blocked — try next client in chain
            continue

        except Exception as e:
            raise RuntimeError(f"Unexpected YouTube download error: {e}") from e

    # All clients exhausted
    raise RuntimeError(
        f"YouTube blocked all download attempts (tried {len(_CLIENT_CHAIN)} clients). "
        f"Last error: {last_error}"
    )


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub"""
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
