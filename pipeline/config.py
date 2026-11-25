"""
Pipeline configuration and constants.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schema" / "storyboard.schema.json"
STORYBOARD_PATH = BASE_DIR / "storyboard.json"
RUNS_LOG_PATH = BASE_DIR / "runs.jsonl"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Sub-output directories
NARRATION_DIR = OUTPUTS_DIR / "narration"
KEYFRAMES_DIR = OUTPUTS_DIR / "keyframes"
SHOTS_DIR = OUTPUTS_DIR / "shots"
MUSIC_DIR = OUTPUTS_DIR / "music"
ASSEMBLY_DIR = OUTPUTS_DIR / "assembly"
EXPORTS_DIR = OUTPUTS_DIR / "exports"

# Ensure all directories exist
for d in [NARRATION_DIR, KEYFRAMES_DIR, SHOTS_DIR, MUSIC_DIR, ASSEMBLY_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME", "")
KAGGLE_KEY = os.getenv("KAGGLE_KEY", "")

def get_ffmpeg_bin() -> str:
    """Finds ffmpeg binary on system."""
    import shutil
    found = shutil.which("ffmpeg")
    if found:
        return found
    winget_path = Path(r"C:\Users\pc\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.1-full_build\bin\ffmpeg.exe")
    if winget_path.exists():
        return str(winget_path)
    return "ffmpeg"


# Media specifications
VIDEO_FPS = 24
TARGET_LUFS = -14.0
LRA = 7.0
TRUE_PEAK = -1.0
DUCKING_THRESHOLD = 0.02
DUCKING_RATIO = 6.0
DUCKING_ATTACK_MS = 300
DUCKING_RELEASE_MS = 1200
