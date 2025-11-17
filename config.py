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
video_gen_api_keys_str = os.getenv("VIDEO_GEN_API_KEYS") 
if not video_gen_api_keys_str:
    raise EnvironmentError("VIDEO_GEN_API_KEYS not set in .env file")
VIDEO_GEN_API_KEYS = video_gen_api_keys_str.split(',')
google_key_rotator = APIKeyRotator(GOOGLE_API_KEYS)
video_gen_key_rotator = APIKeyRotator(VIDEO_GEN_API_KEYS)

# --- PEXELS Key Rotator (NEW) ---
# We now load multiple Pexels keys and create a rotator for them
pexels_api_keys_str = os.getenv("PEXELS_API_KEYS")
if not pexels_api_keys_str:
    raise EnvironmentError("PEXELS_API_KEYS (plural) not set in .env file")
PEXELS_API_KEYS = pexels_api_keys_str.split(',')
pexels_key_rotator = APIKeyRotator(PEXELS_API_KEYS)

# --- Base Temp Dir (Unchanged) ---
BASE_TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_files")
os.makedirs(BASE_TEMP_DIR, exist_ok=True)