# config.py
import os
from dotenv import load_dotenv
from utils.api_key_rotator import APIKeyRotator

# Load environment variables from .env file
load_dotenv()

# --- Google Key Rotator (Unchanged) ---
google_api_keys_str = os.getenv("GOOGLE_API_KEYS")
if not google_api_keys_str:
    raise EnvironmentError("GOOGLE_API_KEYS not set in .env file")
GOOGLE_API_KEYS = google_api_keys_str.split(',')
video_gen_api_keys_str = os.getenv("VIDEO_GEN_API_KEYS", "")
# VIDEO_GEN_API_KEYS is optional - can use Application Default Credentials instead
VIDEO_GEN_API_KEYS = video_gen_api_keys_str.split(',') if video_gen_api_keys_str else []
google_key_rotator = APIKeyRotator(GOOGLE_API_KEYS)
# Only create rotator if we have keys, otherwise it will use ADC
video_gen_key_rotator = APIKeyRotator(VIDEO_GEN_API_KEYS) if VIDEO_GEN_API_KEYS else None

# --- Gemini 3 Pro Key (for script generation) ---
GEMINI_3_PRO_KEY = os.getenv("GEMINI_3_PRO_KEY", "")

# --- PEXELS Key Rotator (NEW) ---
# We now load multiple Pexels keys and create a rotator for them
pexels_api_keys_str = os.getenv("PEXELS_API_KEYS")
if not pexels_api_keys_str:
    raise EnvironmentError("PEXELS_API_KEYS (plural) not set in .env file")
PEXELS_API_KEYS = pexels_api_keys_str.split(',')
pexels_key_rotator = APIKeyRotator(PEXELS_API_KEYS)

# --- Freesound API Key (NEW) ---
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")
# We don't strictly need a rotator if we only have one key, but good to have if we expand later
# For now, just a single key string is fine
if not FREESOUND_API_KEY:
    print("⚠️  FREESOUND_API_KEY not set in .env file. Background music will be disabled.")

# --- Base Temp Dir (Unchanged) ---
BASE_TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_files")
os.makedirs(BASE_TEMP_DIR, exist_ok=True)