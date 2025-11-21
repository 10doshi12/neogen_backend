
import os
import sys
from services.audio_service import search_music
from config import FREESOUND_API_KEY

def test_search_music():
    print(f"Testing with API Key: {FREESOUND_API_KEY[:5]}..." if FREESOUND_API_KEY else "No API Key set")
    
    if not FREESOUND_API_KEY:
        print("Skipping test because FREESOUND_API_KEY is not set")
        return

    # Test 1: Search for upbeat music
    print("\n--- Test 1: Upbeat Music ---")
    path1 = search_music("upbeat pop", duration=15)
    if path1 and os.path.exists(path1):
        print(f"SUCCESS: Downloaded to {path1}")
        print(f"File size: {os.path.getsize(path1)} bytes")
    else:
        print("FAILURE: Could not download upbeat music")

    # Test 2: Search for cinematic music
    print("\n--- Test 2: Cinematic Music ---")
    path2 = search_music("cinematic ambient", duration=10)
    if path2 and os.path.exists(path2):
        print(f"SUCCESS: Downloaded to {path2}")
        print(f"File size: {os.path.getsize(path2)} bytes")
    else:
        print("FAILURE: Could not download cinematic music")

if __name__ == "__main__":
    test_search_music()
