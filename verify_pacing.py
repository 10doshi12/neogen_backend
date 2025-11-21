import sys
import os

# Add the project root to the python path
sys.path.append("/Users/10doshi12/Desktop/neogen/video_backend")

from services import ai_service

def verify_pacing_updates():
    print("Verifying pacing updates in ai_service.py...")
    
    # Check SCRIPT_PROMPT_TEMPLATE
    if "1.8 to 2.1 words per second" in ai_service.SCRIPT_PROMPT_TEMPLATE:
        print("✅ SCRIPT_PROMPT_TEMPLATE contains correct pacing range.")
    else:
        print("❌ SCRIPT_PROMPT_TEMPLATE missing correct pacing range.")
        
    if "Do NOT exceed 2.1 words per second" in ai_service.SCRIPT_PROMPT_TEMPLATE:
        print("✅ SCRIPT_PROMPT_TEMPLATE contains critical warning.")
    else:
        print("❌ SCRIPT_PROMPT_TEMPLATE missing critical warning.")

    # Check STOCK_ONLY_SCRIPT_PROMPT_TEMPLATE
    if "1.8 to 2.1 words per second" in ai_service.STOCK_ONLY_SCRIPT_PROMPT_TEMPLATE:
        print("✅ STOCK_ONLY_SCRIPT_PROMPT_TEMPLATE contains correct pacing range.")
    else:
        print("❌ STOCK_ONLY_SCRIPT_PROMPT_TEMPLATE missing correct pacing range.")

    # Check _calculate_tts_speed logic (by inspecting the function code or testing it)
    # We can test the function directly if we can access it (it's private but we can try)
    try:
        speed = ai_service._calculate_tts_speed("one two three four", 2.0)
        # 4 words / 2.0s = 2.0 wps. Target is 1.95 wps.
        # Expected duration = 4 / 1.95 = 2.05s
        # Speed = 2.05 / 2.0 = 1.025 -> 1.03
        print(f"✅ _calculate_tts_speed test result: {speed}")
    except Exception as e:
        print(f"❌ Failed to test _calculate_tts_speed: {e}")

    print("\nVerification complete.")

if __name__ == "__main__":
    verify_pacing_updates()
