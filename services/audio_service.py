import requests
import os
import random
from config import FREESOUND_API_KEY, BASE_TEMP_DIR

def search_music(query: str, duration: int = 15) -> str:
    """
    Searches Freesound for music tracks matching the query and duration.
    Downloads the preview file (MP3/OGG) and returns the path.
    
    Args:
        query: Search keywords (e.g., "upbeat pop", "cinematic ambient")
        duration: Target duration in seconds (used to filter results)
        
    Returns:
        Path to the downloaded audio file, or None if no suitable track found.
    """
    if not FREESOUND_API_KEY:
        print("⚠️  FREESOUND_API_KEY not set. Skipping music search.")
        return None
        
    print(f"🎵 Searching Freesound for: '{query}' (duration ~{duration}s)")
    
    # Freesound Text Search API
    search_url = "https://freesound.org/apiv2/search/text/"
    
    # Filter for music-like sounds
    # duration: [duration-5 TO duration+15] to find tracks that are long enough but not too long
    # tag:music OR tag:loop to find musical content
    min_duration = max(5, duration - 5)
    max_duration = duration + 30 # Allow longer tracks, we can trim
    
    params = {
        "query": query,
        "token": FREESOUND_API_KEY,
        "filter": f"duration:[{min_duration} TO {max_duration}] tag:music",
        "sort": "rating_desc", # Get high-quality tracks
        "fields": "id,name,previews,duration,username",
        "page_size": 10
    }
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            count = results.get('count', 0)
            print(f"✅ Found {count} results on Freesound.")
            
            if count == 0:
                print(f"❌ No music found for '{query}'.")
                return None
                
            # Pick a random track from top 5 to add variety
            items = results.get('results', [])
            if not items:
                return None
                
            # Filter out items without previews
            valid_items = [item for item in items if 'previews' in item and 'preview-hq-mp3' in item['previews']]
            
            if not valid_items:
                print("❌ No valid previews found.")
                return None
                
            # Select top 3 and pick one randomly
            selection = random.choice(valid_items[:3])
            
            preview_url = selection['previews']['preview-hq-mp3']
            track_name = selection['name']
            track_id = selection['id']
            username = selection['username']
            
            print(f"✅ Selected track: '{track_name}' by {username} (ID: {track_id})")
            
            # Download
            output_filename = f"freesound_{track_id}.mp3"
            output_path = os.path.join(BASE_TEMP_DIR, output_filename)
            
            if os.path.exists(output_path):
                print(f"  → File already exists: {output_path}")
                return output_path
                
            print(f"⬇️  Downloading preview from: {preview_url}")
            with requests.get(preview_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
            print(f"✅ Music saved to: {output_path}")
            return output_path
            
        else:
            print(f"❌ Freesound API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching/downloading music: {e}")
        return None
