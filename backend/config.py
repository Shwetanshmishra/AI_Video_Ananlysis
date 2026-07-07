import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
CHROMA_DIR = os.getenv("CHROMA_DIR", "vector_db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
