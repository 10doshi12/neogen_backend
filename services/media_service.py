# services/media_service.py
import requests
import os
import time
# Import our new rotator from config
from config import pexels_key_rotator, BASE_TEMP_DIR 

def get_stock_video(query: str, output_path: str, orientation: str = "horizontal") -> str:
    """
    Searches Pexels for a video using the direct API, downloads it,
    and saves it to output_path.
    
    Args:
        query: Search query
        output_path: Path to save the video
        orientation: "horizontal" (16:9) or "vertical" (9:16)
    """
    
    # Map our orientation to Pexels orientation
    # Pexels supports: landscape, portrait, square
    pexels_orientation = "landscape"
    if orientation == "vertical":
        pexels_orientation = "portrait"
    
    # --- Part 1: Search for Video (Your 'search_for_video' logic) ---
    search_url = "https://api.pexels.com/videos/search"
    params = { "query": query, "per_page": 10, "orientation": pexels_orientation }
    max_retries = len(pexels_key_rotator.api_keys)
    video_url = None
    
    print(f"⌛ Searching Pexels for: '{query}'")

    for attempt in range(max_retries):
        # Use our rotator from config
        api_key = pexels_key_rotator.get_key() 
        headers = {"Authorization": api_key}
        key_short = api_key[:5] + "..."

        try:
            response = requests.get(search_url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                print(f"✅ Success with Pexels key {key_short}")
                results = response.json()
                
                if not results.get("videos"):
                    print(f"❌ No video results found for '{query}'.")
                    # Break loop, no video will be found
                    break 

                first_video = results["videos"][0]
                best_link = None
                
                for file_info in first_video.get("video_files", []):
                    if file_info.get("quality") == "hd":
                        best_link = file_info.get("link")
                        break
                
                if not best_link and first_video.get("video_files"):
                    best_link = first_video["video_files"][0].get("link")

                print(f"✅ Found video. URL: {best_link}")
                video_url = best_link
                # Success! Exit the retry loop
                break 

            elif response.status_code == 429:
                print(f"⚠️ Pexels key {key_short} rate-limited. Rotating key. (Attempt {attempt + 1}/{max_retries})")
                time.sleep(1)
            
            else:
                print(f"❌ Pexels key {key_short} failed ({response.status_code}). Rotating key.")
                time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"❌ Pexels request with key {key_short} failed: {e}. Rotating key.")
            time.sleep(1)

    # --- Check if search was successful ---
    if not video_url:
        print(f"❌ All Pexels keys failed or no video was found for query: '{query}'")
        raise ValueError(f"No video found for query: {query}. All keys failed or no results.")

    # --- Part 2: Download Video (Your 'download_video' logic) ---
    try:
        print(f"⌛ Downloading video from: {video_url}")
        with requests.get(video_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"\n✅ Success! Video saved to: {output_path}")
        # Return the path, as our service expects
        return output_path 
        
    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred downloading video: {e}")
        raise
    except Exception as e:
        print(f"❌ An error occurred saving file: {e}")
        raise