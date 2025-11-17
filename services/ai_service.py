# services/ai_service.py
import google.generativeai as genai
import json
import re
import wave  # <-- ADDED IMPORT
from config import google_key_rotator # Import the rotator instance
from schemas import ScriptResponse

# --- SCRIPT PROMPT (Unchanged) ---
SCRIPT_PROMPT_TEMPLATE = """
You are a creative video scriptwriter. A user wants a promo video.
Generate a script for a video based on this prompt: "{user_prompt}"

The script must be broken down into 3-5 scenes.
The total duration must be atleast 15-20 seconds if duration is not explicitly mentioned inside the "{user_prompt}".
For each scene, provide:
1.  `scene_number`: The order of the scene.
2.  `media_type`: Always "video". Do not use "image".
3.  `search_query`: A 3-7 word, simple, concrete search query for a stock video site like Pexels (e.g., "coffee shop", "person running", "energetic fitness"). DO NOT use long sentences or descriptions.
4.  `voiceover_text`: A short voiceover script for this scene.
5.  `duration_seconds`: How long this scene should be. Use only whole numbers (integers) for this value.

Return your response as a single, valid JSON object that matches this structure:
{{
    "title": "A short, catchy video title",
    "scenes": [
        {{
            "scene_number": 1,
            "media_type": "video",
            "search_query": "...",
            "voiceover_text": "...",
            "duration_seconds": ...
        }}
    ]
}}

Ensure the sum of all scene "duration_seconds" is nearly 15-20 seconds if not explicitly mentioned.
Do not include any text, notes, or markdown (like ```json) before or after the JSON object.
"""

# --- _clean_json_response (Unchanged) ---
def _clean_json_response(text: str) -> str:
    """
    Finds and extracts the first valid JSON object from a string.
    """
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("No valid JSON object found in AI response.")

# --- generate_script (Unchanged) ---
def generate_script(prompt: str) -> ScriptResponse:
    """
    Generates the video script using Gemini 2.5 Flash, with key rotation.
    """
    num_keys = len(google_key_rotator.api_keys)
    
    for i in range(num_keys):
        api_key = google_key_rotator.get_key()
        print(f"--- Attempting script generation with key ...{api_key[-4:]} (try {i+1}/{num_keys}) ---")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        full_prompt = SCRIPT_PROMPT_TEMPLATE.format(
            user_prompt=prompt
        )
        
        try:
            response = model.generate_content(full_prompt)
            cleaned_json = _clean_json_response(response.text)
            script_data = json.loads(cleaned_json)
            return ScriptResponse(**script_data)
            
        except Exception as e:
            error_message = str(e).lower()
            if "429" in error_message or "quota" in error_message:
                print(f"Quota exceeded for key ...{api_key[-4:]}. Trying next key...")
                continue
            else:
                print(f"Error generating script with key ...{api_key[-4:]}: {e}")
                raise ValueError(f"Failed to generate or parse script: {e}")
    
    raise ValueError("Failed to generate script: All Google API keys are rate-limited.")

# -----------------------------------------------------------------
# --- NEW HELPER FUNCTION (From you) ---
# -----------------------------------------------------------------
def save_pcm_to_wav(
    output_path: str,
    pcm_data: bytes,
    channels: int = 1,
    sample_width: int = 2,
    frame_rate: int = 24000
):
    """
    Saves raw PCM audio data to a valid WAV file with the correct header.
    """
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(frame_rate)
        wf.writeframes(pcm_data)
    print(f"--- Valid WAV file saved ---\nSaved to {output_path}\n--------------------")


# -----------------------------------------------------------------
# --- UPDATED generate_audio FUNCTION ---
# -----------------------------------------------------------------
def generate_audio(text: str, output_path: str) -> str:
    """
    Generates TTS audio using Gemini 2.5 Flash Preview TTS, with key rotation.
    Saves the audio to a valid WAV file.
    """
    num_keys = len(google_key_rotator.api_keys)
    
    # We must save as .wav since the API returns raw PCM data
    # Ensure the output_path ends in .wav
    if not output_path.lower().endswith(".wav"):
        output_path = f"{output_path}.wav"

    for i in range(num_keys):
        api_key = google_key_rotator.get_key()
        print(f"--- Requesting audio with key ...{api_key[-4:]} (try {i+1}/{num_keys}) ---")
        genai.configure(api_key=api_key)

        try:
            # --- USING YOUR WORKING MODEL CONFIG ---
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash-preview-tts',
                generation_config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": "Kore"}
                        }
                    }
                }
            )
            
            print(f"--- Requesting audio from Gemini for: '{text}' ---")
            response = model.generate_content(f"Say this: {text}")

            if (not response.candidates[0] or
                not response.candidates[0].content or
                not response.candidates[0].content.parts or
                not response.candidates[0].content.parts[0].inline_data):
                raise Exception("Gemini TTS returned no audio data.")

            # Get the raw PCM audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data

            # --- USING YOUR WORKING SAVE FUNCTION ---
            # Save the raw PCM data as a valid WAV file
            save_pcm_to_wav(output_path, audio_data)
            
            print(f"✅ Audio generated and saved to: {output_path}")
            # Success! Return the path.
            return output_path
            
        except Exception as e:
            error_message = str(e).lower()
            if "429" in error_message or "quota" in error_message:
                print(f"Quota exceeded for key ...{api_key[-4:]}. Trying next key...")
                continue # Go to the next iteration of the loop
            else:
                # This is a different error, raise it
                print(f"Error generating audio with key ...{api_key[-4:]}: {e}")
                raise ValueError(f"Failed to generate audio: {e}")

    # If the loop finishes without returning, all keys are exhausted
    raise ValueError("Failed to generate audio: All Google API keys are rate-limited.")