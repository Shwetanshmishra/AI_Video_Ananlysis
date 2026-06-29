from pydub import AudioSegment
import os
import yt_dlp

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ydl_opts = {
        # Prefer m4a audio, then any best audio
        "format": "bestaudio[ext=m4a]/bestaudio/best",

        "outtmpl": output_path,

        # Don't download playlists
        "noplaylist": True,

        # Ignore harmless warnings
        "quiet": True,
        "no_warnings": True,

        # Retry on temporary failures
        "retries": 10,
        "fragment_retries": 10,

        # Avoid certificate issues on some hosts
        "nocheckcertificate": True,

        # Force IPv4 (helps on some cloud providers)
        "source_address": "0.0.0.0",

        # Use Android/Web client
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },

        # Better HTTP headers
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0 Safari/537.36"
            )
        },

        # Convert to WAV automatically
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        base = os.path.splitext(filename)[0]
        wav_file = base + ".wav"

        if os.path.exists(wav_file):
            return wav_file

        raise FileNotFoundError("yt-dlp completed but WAV file was not created.")

    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"Failed to download YouTube audio: {e}") from e

    except Exception as e:
        raise RuntimeError(f"Unexpected YouTube download error: {e}") from e



def convert_to_wav(input_path : str) -> str:
    """Convert any audio/video file to WAV format using pydub"""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio= AudioSegment.from_file(input_path)
    audio= audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path



def chunk_audio(wav_path : str , chunk_minutes : int=10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms= chunk_minutes *60 *1000
    
    chunks=[]
    for i,start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        
        chunks.append(chunk_path)
    return chunks

def process_input(source : str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detectd local file. Converting to WAV...")
        wav_path = convert_to_wav(source)
        
    print("Chunking Audio...")
    chunks = chunk_audio(wav_path)
    print(f'Audio ready - {len(chunks)} chunk(s) created.')
    return chunks