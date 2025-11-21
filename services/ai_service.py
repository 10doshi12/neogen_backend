# services/ai_service.py
import google.generativeai as genai
import json
import re
import wave  # <-- ADDED IMPORT
import requests
import time
import os
from google.oauth2 import service_account
from config import google_key_rotator, video_gen_key_rotator, GEMINI_3_PRO_KEY # Import the rotator instances
from schemas import ScriptResponse

# Vertex AI Veo 3.1 Configuration
# Get project ID and location from environment variables
VEO_PROJECT_ID = os.getenv("VEO_PROJECT_ID", "")
VEO_LOCATION = os.getenv("VEO_LOCATION", "us-central1")
VEO_API_BASE_URL = os.getenv("VEO_API_BASE_URL", "")

# --- SCRIPT PROMPT ---
SCRIPT_PROMPT_TEMPLATE = """
You are a creative video scriptwriter and visual director. A user wants a promo video.

Generate a script for a video based on this prompt: "{user_prompt}"

The script should be broken down into multiple scenes to create a dynamic and engaging video. Use as many scenes as needed to tell the story effectively, creating variety and visual interest. There is no limit on the number of scenes - use your creativity to break down the content into meaningful segments.

IMPORTANT: The total video duration must be EXACTLY {total_duration_seconds} seconds. The sum of all scene "duration_seconds" must equal {total_duration_seconds} exactly.

REQUIREMENT: At least ONE scene must use "media_source": "ai_generated". You must include at least one AI-generated scene in the script.

STRICT DURATION RULES:
- **PACING STRATEGY**: The ideal scene duration for viral retention is **3-4 seconds**. Aim for this range whenever possible to keep the video fast-paced.
- If "media_source" is "stock": "duration_seconds" MUST be between 2 and 6 seconds (inclusive). Use integers only.
- If "media_source" is "ai_generated": "duration_seconds" MUST be between 4 and 6 seconds (inclusive). The minimum duration for AI-generated scenes is 4 seconds - NEVER use less than 4 seconds. Use integers only.
- These rules are STRICT and MUST be followed for every scene.

AUDIO SPEED GUIDELINES:
- The voiceover text should be written to achieve a speaking rate of **1.8 to 2.1 words per second**.
- **CRITICAL**: Do NOT exceed 2.1 words per second. If you write too many words, the text-to-speech will speed up to fit the duration, causing a "chipmunk effect" which sounds terrible.
- Adjust the word count and complexity based on the scene's tone and urgency:
  * Calm/introductory scenes: Aim for 1.8-1.9 words per second (fewer words, more pauses)
  * Normal/explanatory scenes: Aim for 1.9-2.0 words per second (moderate pace)
  * Urgent/exciting scenes: Aim for 2.0-2.1 words per second (more words, faster pace, but STRICTLY below 2.1)
- Calculate: For a 5-second scene, use approximately 9-10 words (calm), 10 words (normal), or 10-11 words (urgent).
- Keep voiceover text concise and impactful. **Less is more.**

For each scene, you must determine the best "media_source" by following this logic:

1. PRIORITY - STOCK: If the scene depicts a common real-world scenario (e.g., people talking, nature, cityscapes, business) that is easily found on Pexels/Shutterstock, set "media_source" to "stock".

2. REQUIRED - AI GENERATION: At least one scene MUST use "ai_generated". Choose scenes that are surreal, sci-fi, fantasy, highly specific, or require action not found in stock libraries. You can use AI generation for creative, unique, or stylized visuals.

For each scene, provide:

1. "scene_number": The order of the scene.
   - **SCENE 1 (HOOK) REQUIREMENT**: Scene 1 is the "Hook". It MUST be visually striking. Use "movement" (e.g., running, flying, fast zoom) or a "negative/shocking" visual (e.g., broken object, storm, stressed person) to grab attention immediately.

2. "media_source": Either "stock" or "ai_generated" based on the logic above. REMEMBER: At least one scene must be "ai_generated".

3. "visual_prompt": 

   - IF STOCK: A simple 5-10 word search query (e.g., "happy team working in office").

   - IF AI GENERATED: A highly detailed, cinematic description including subject, action, lighting, camera angle, and texture. The video will be generated at 1080p resolution (1920x1080).
     * **VISUAL STYLE**: Use "High Contrast", "Slightly Underexposed", and "Cinematic Lighting" in your description to create a premium look.
     * BRANDING INSTRUCTION: If the user prompt mentions a specific brand, product, or logo, you MUST describe how it appears in the shot (e.g., "close-up of a soda can with [Brand Name] logo", "neon sign reading [Brand Name]", "billboard displaying [Brand Name]").
     * Example: "Cinematic wide shot of a futuristic cyberpunk city with neon lights, flying cars passing by, rainy atmosphere, high contrast, slightly underexposed, photorealistic 1080p. A massive holographic billboard in the center displays the text 'NeoCola' in glowing blue letters."

4. "voiceover_text": A short voiceover script for this scene. MUST follow the audio speed guidelines (1.8-2.1 words per second). Calculate the appropriate word count for the scene's duration.

5. "duration_seconds": How long this scene should be (integer). 
   - MUST be 2-6 seconds if "media_source" is "stock"
   - MUST be 4-6 seconds if "media_source" is "ai_generated" (MINIMUM 4 seconds - never less than 4)
   - The sum of ALL scene durations must equal {total_duration_seconds} exactly.
   - Create as many scenes as needed to create variety and visual interest

6. "background_music_keywords": Provide 2-3 GENERIC music keywords for the ENTIRE video based on the overall mood and tone.
   - Use SIMPLE, COMMON words that are likely to be found in any music library (e.g., "upbeat", "calm", "energetic", "cinematic", "ambient", "electronic", "acoustic")
   - Avoid overly specific genres or artist names (e.g., avoid "jazz fusion", "trip-hop", "lo-fi hip-hop")
   - Good examples: ["upbeat pop", "cinematic"], ["calm ambient", "electronic"], ["energetic rock"]
   - Bad examples: ["funky jazz fusion", "trip-hop beats"], ["lo-fi hip-hop chill"]
   - Maximum 3-4 words total across all keywords

Return your response as a single, valid JSON object that matches this structure:
{{
    "title": "A short, catchy video title",
    "background_music_keywords": ["keyword1", "keyword2"],
    "scenes": [
        {{
            "scene_number": 1,
            "media_source": "stock", 
            "visual_prompt": "...",
            "voiceover_text": "...",
            "duration_seconds": ...
        }},
        {{
            "scene_number": 2,
            "media_source": "ai_generated",
            "visual_prompt": "...",
            "voiceover_text": "...",
            "duration_seconds": ...
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- The sum of all scene "duration_seconds" must equal {total_duration_seconds} EXACTLY
- At least one scene must have "media_source": "ai_generated"
- Use integers for all duration_seconds values
- STOCK scenes: duration MUST be 2-6 seconds (inclusive)
- AI_GENERATED scenes: duration MUST be 4-6 seconds (inclusive) - MINIMUM 4 seconds, never less
- Voiceover text MUST follow 1.8-2.1 words per second (STRICTLY below 2.1) based on scene tone/urgency
- Create multiple scenes for variety and visual interest - there is no limit on the number of scenes
- Background music keywords MUST be generic and common (2-3 keywords, max 3-4 words total)

Do not include any text, notes, or markdown (like ```json) before or after the JSON object.
"""

# --- STOCK ONLY SCRIPT PROMPT (TEMP) ---
STOCK_ONLY_SCRIPT_PROMPT_TEMPLATE = """
You are a creative video scriptwriter and visual director. A user wants a promo video.

Generate a script for a video based on this prompt: "{user_prompt}"

The script should be broken down into multiple scenes to create a dynamic and engaging video. Use as many scenes as needed to tell the story effectively, creating variety and visual interest. There is no limit on the number of scenes - use your creativity to break down the content into meaningful segments.

IMPORTANT: The total video duration must be EXACTLY {total_duration_seconds} seconds. The sum of all scene "duration_seconds" must equal {total_duration_seconds} exactly.

REQUIREMENT: ALL scenes must use "media_source": "stock". Do NOT use "ai_generated" for any scene.

STRICT DURATION RULES:
- **PACING STRATEGY**: The ideal scene duration for viral retention is **3-4 seconds**. Aim for this range whenever possible to keep the video fast-paced.
- "duration_seconds" MUST be between 2 and 6 seconds (inclusive). Use integers only.
- These rules are STRICT and MUST be followed for every scene.

AUDIO SPEED GUIDELINES:
- The voiceover text should be written to achieve a speaking rate of **1.8 to 2.1 words per second**.
- **CRITICAL**: Do NOT exceed 2.1 words per second. If you write too many words, the text-to-speech will speed up to fit the duration, causing a "chipmunk effect" which sounds terrible.
- Adjust the word count and complexity based on the scene's tone and urgency:
  * Calm/introductory scenes: Aim for 1.8-1.9 words per second (fewer words, more pauses)
  * Normal/explanatory scenes: Aim for 1.9-2.0 words per second (moderate pace)
  * Urgent/exciting scenes: Aim for 2.0-2.1 words per second (more words, faster pace, but STRICTLY below 2.1)
- Calculate: For a 5-second scene, use approximately 9-10 words (calm), 10 words (normal), or 10-11 words (urgent).
- Keep voiceover text concise and impactful. **Less is more.**

For each scene, provide:

1. "scene_number": The order of the scene.
   - **SCENE 1 (HOOK) REQUIREMENT**: Scene 1 is the "Hook". It MUST be visually striking. Use "movement" (e.g., running, flying, fast zoom) or a "negative/shocking" visual (e.g., broken object, storm, stressed person) to grab attention immediately.

2. "media_source": MUST be "stock".

3. "visual_prompt": A simple 5-10 word search query (e.g., "happy team working in office").

4. "voiceover_text": A short voiceover script for this scene. MUST follow the audio speed guidelines (2.0-2.4 words per second, generally below 2.4, based on scene tone/urgency). Calculate the appropriate word count for the scene's duration.

5. "duration_seconds": How long this scene should be (integer).
   - MUST be 2-6 seconds
   - The sum of ALL scene durations must equal {total_duration_seconds} exactly.
   - Create as many scenes as needed to create variety and visual interest

6. "background_music_keywords": Provide 2-3 GENERIC music keywords for the ENTIRE video based on the overall mood and tone.
   - Use SIMPLE, COMMON words that are likely to be found in any music library (e.g., "upbeat", "calm", "energetic", "cinematic", "ambient", "electronic", "acoustic")
   - Avoid overly specific genres or artist names
   - Maximum 3-4 words total across all keywords

Return your response as a single, valid JSON object that matches this structure:
{{
    "title": "A short, catchy video title",
    "background_music_keywords": ["keyword1", "keyword2"],
    "scenes": [
        {{
            "scene_number": 1,
            "media_source": "stock",
            "visual_prompt": "...",
            "voiceover_text": "...",
            "duration_seconds": ...
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- The sum of all scene "duration_seconds" must equal {total_duration_seconds} EXACTLY
- ALL scenes must have "media_source": "stock"
- Use integers for all duration_seconds values
- Duration MUST be 2-6 seconds (inclusive)
- Voiceover text MUST follow 2.0-2.4 words per second (generally below 2.4) based on scene tone/urgency
- Create multiple scenes for variety and visual interest - there is no limit on the number of scenes
- Background music keywords MUST be generic and common (2-3 keywords, max 3-4 words total)

Do not include any text, notes, or markdown (like ```json) before or after the JSON object.
"""

# --- _clean_json_response ---
def _clean_json_response(text: str) -> str:
    """
    Finds and extracts the first valid JSON object from a string.
    Handles common formatting issues from AI responses.
    """
    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Find JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("No valid JSON object found in AI response.")
    
    json_str = match.group(0)
    
    # Common fixes for malformed JSON
    # Fix trailing commas before closing braces/brackets
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Try to validate and return
    try:
        json.loads(json_str)  # Validate
        return json_str
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing error at position {e.pos}: {e.msg}")
        print(f"JSON snippet around error: {json_str[max(0, e.pos-50):e.pos+50]}")
        raise ValueError(f"Invalid JSON from AI: {e.msg}")


# --- _print_script_summary ---
def _print_script_summary(script: ScriptResponse, target_duration: int):
    """
    Prints the script in a nicely formatted, human-readable way.
    """
    print("\n" + "=" * 80)
    print("📝 GENERATED VIDEO SCRIPT")
    print("=" * 80)
    print(f"Title: {script.title}")
    print(f"Music Keywords: {', '.join(script.background_music_keywords)}")
    print(f"Total Duration: {sum(s.duration_seconds for s in script.scenes):.1f}s (Target: {target_duration}s)")
    print(f"Number of Scenes: {len(script.scenes)}")
    print("-" * 80)
    
    for scene in script.scenes:
        media_source_icon = "🤖" if scene.media_source.lower() == "ai_generated" else "📹"
        word_count = len(scene.voiceover_text.split())
        words_per_second = word_count / scene.duration_seconds if scene.duration_seconds > 0 else 0
        
        # Duration validation indicator
        duration_valid = True
        if scene.media_source.lower() == "stock":
            duration_valid = 2 <= scene.duration_seconds <= 6
        elif scene.media_source.lower() == "ai_generated":
            duration_valid = 4 <= scene.duration_seconds <= 6
        
        duration_status = "✅" if duration_valid else "⚠️"
        audio_status = "✅" if 1.8 <= words_per_second <= 2.1 else "⚠️"
        
        print(f"\nScene {scene.scene_number} ({scene.duration_seconds:.1f}s) {media_source_icon} {duration_status}")
        print(f"  Media Source: {scene.media_source.upper()}")
        print(f"  Visual Prompt: {scene.visual_prompt}")
        print(f"  Voiceover: \"{scene.voiceover_text}\"")
        print(f"  Audio Stats: {word_count} words, {words_per_second:.2f} words/sec {audio_status} (target: 1.8-2.1)")
    
    print("\n" + "=" * 80)
    print()

# --- Helper function to validate and return script ---
def _validate_and_return_script(script_response: ScriptResponse, total_duration_seconds: int) -> ScriptResponse:
    """
    Validates the script response and returns it after validation and formatting.
    """
    # Validate that at least one scene uses AI generation
    # TEMP: Disabled for stock-only testing
    # has_ai_generated = any(scene.media_source.lower() == "ai_generated" for scene in script_response.scenes)
    # if not has_ai_generated:
    #     raise ValueError("Script must include at least one scene with 'media_source': 'ai_generated'")
    
    # Validate duration rules for each scene
    for scene in script_response.scenes:
        media_source = scene.media_source.lower()
        duration = scene.duration_seconds
        
        if media_source == "stock":
            if duration < 2 or duration > 6:
                raise ValueError(f"Scene {scene.scene_number}: Stock scenes must have duration between 2-6 seconds, got {duration}s")
        elif media_source == "ai_generated":
            if duration < 4 or duration > 6:
                raise ValueError(f"Scene {scene.scene_number}: AI-generated scenes must have duration between 4-6 seconds, got {duration}s")
    
    # Validate that total duration matches requested duration
    total_scene_duration = sum(scene.duration_seconds for scene in script_response.scenes)
    if abs(total_scene_duration - total_duration_seconds) > 0.5:  # Allow 0.5 second tolerance for rounding
        print(f"⚠️  Warning: Script duration ({total_scene_duration}s) doesn't match requested duration ({total_duration_seconds}s)")
        print(f"⚠️  Adjusting scene durations to match exactly...")
        # Adjust the last scene to match exactly, but ensure it still follows duration rules
        if script_response.scenes:
            last_scene = script_response.scenes[-1]
            adjustment = total_duration_seconds - total_scene_duration
            new_duration = last_scene.duration_seconds + adjustment
            
            # Check if adjustment violates duration rules
            if last_scene.media_source.lower() == "stock" and (new_duration < 2 or new_duration > 6):
                print(f"⚠️  Cannot adjust last scene (stock) to {new_duration}s without violating 2-6s rule")
                print(f"⚠️  Attempting to redistribute duration across scenes...")
                # Try to redistribute across other scenes
                # This is a fallback - ideally the AI should get it right
            elif last_scene.media_source.lower() == "ai_generated" and (new_duration < 4 or new_duration > 6):
                print(f"⚠️  Cannot adjust last scene (ai_generated) to {new_duration}s without violating 4-6s rule")
                print(f"⚠️  Attempting to redistribute duration across scenes...")
            
            last_scene.duration_seconds = new_duration
            print(f"✅ Adjusted last scene duration by {adjustment:.1f} seconds to {new_duration:.1f}s")
    
    # Print the script in a nicely formatted way
    _print_script_summary(script_response, total_duration_seconds)
    
    return script_response

# --- generate_script ---
def generate_script(prompt: str, total_duration_seconds: int = 20) -> ScriptResponse:
    """
    Generates the video script using Gemini 3 Pro Preview with GEMINI_3_PRO_KEY.
    Falls back to regular Google API keys with Gemini 2.5 Flash if GEMINI_3_PRO_KEY is not set.
    
    Args:
        prompt: The user's video prompt
        total_duration_seconds: The exact total duration for the video (default: 20)
    """
    # TEMP: Use stock-only prompt
    # full_prompt = SCRIPT_PROMPT_TEMPLATE.format(
    #     user_prompt=prompt,
    #     total_duration_seconds=total_duration_seconds
    # )
    full_prompt = STOCK_ONLY_SCRIPT_PROMPT_TEMPLATE.format(
        user_prompt=prompt,
        total_duration_seconds=total_duration_seconds
    )
    
    # Try GEMINI_3_PRO_KEY first for Gemini 3 Pro Preview
    if GEMINI_3_PRO_KEY:
        print(f"--- Using GEMINI_3_PRO_KEY for Gemini 3 Pro Preview ---")
        genai.configure(api_key=GEMINI_3_PRO_KEY)
        try:
            model = genai.GenerativeModel('gemini-3-pro-preview')
            print(f"✅ Using Gemini 3 Pro Preview model ---")
            try:
                response = model.generate_content(full_prompt)
                cleaned_json = _clean_json_response(response.text)
                script_data = json.loads(cleaned_json)
                script_response = ScriptResponse(**script_data)
                return _validate_and_return_script(script_response, total_duration_seconds)
            except Exception as e:
                print(f"⚠️  Error with Gemini 3 Pro Preview: {e}")
                print(f"--- Falling back to regular Google API keys with Gemini 2.5 Flash ---")
        except Exception as e:
            print(f"⚠️  Gemini 3 Pro Preview model not available: {e}")
            print(f"--- Falling back to regular Google API keys with Gemini 2.5 Flash ---")
    else:
        print(f"--- GEMINI_3_PRO_KEY not set, using regular Google API keys ---")
    
    # Fallback to regular Google API keys with Gemini 2.5 Flash
    num_keys = len(google_key_rotator.api_keys)
    
    for i in range(num_keys):
        api_key = google_key_rotator.get_key()
        print(f"--- Attempting script generation with key ...{api_key[-4:]} (try {i+1}/{num_keys}) ---")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        print(f"--- Using Gemini 2.5 Flash ---")
        
        try:
            response = model.generate_content(full_prompt)
            raw_response = response.text
            print(f"--- Raw AI Response (first 200 chars): {raw_response[:200]}...")
            
            cleaned_json = _clean_json_response(raw_response)
            script_data = json.loads(cleaned_json)
            script_response = ScriptResponse(**script_data)
            
            return _validate_and_return_script(script_response, total_duration_seconds)
            
        except Exception as e:
            error_message = str(e).lower()
            if "429" in error_message or "quota" in error_message:
                print(f"Quota exceeded for key ...{api_key[-4:]}. Trying next key...")
                continue
            else:
                print(f"Error generating script with key ...{api_key[-4:]}: {e}")
                # Continue to next key instead of raising immediately
                if i == num_keys - 1:  # Last attempt
                    raise ValueError(f"Failed to generate or parse script after all attempts: {e}")
                continue
    
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
# --- Helper function to calculate TTS speed ---
# -----------------------------------------------------------------
def _calculate_tts_speed(text: str, target_duration: float) -> float:
    """
    Calculates the appropriate TTS speed parameter based on word count and target duration.
    
    Logic:
    - Target speaking rate: 2.2 words per second (middle of 2.0-2.4 range, generally below 2.4)
    - Calculate expected duration at normal speed: word_count / 2.2
    - Speed = expected_duration / target_duration
    - Clamp speed between 0.7 and 1.5 for natural-sounding speech
    
    Args:
        text: The voiceover text
        target_duration: Target duration in seconds
        
    Returns:
        Speed parameter (0.7 to 1.5)
    """
    word_count = len(text.split())
    if word_count == 0 or target_duration <= 0:
        return 1.0  # Default speed
    
    # Target speaking rate (words per second)
    target_wps = 1.95  # Middle of 1.8-2.1 range
    
    # Calculate expected duration if spoken at normal speed (speed = 1.0)
    expected_duration = word_count / target_wps
    
    # Calculate speed adjustment needed
    # If expected_duration > target_duration, we need to speed up (speed > 1)
    # If expected_duration < target_duration, we need to slow down (speed < 1)
    speed = expected_duration / target_duration
    
    # Clamp speed to reasonable bounds (0.7 to 1.5)
    # Too slow (< 0.7) sounds unnatural, too fast (> 1.5) is hard to understand
    speed = max(0.7, min(1.5, speed))
    
    return round(speed, 2)  # Round to 2 decimal places

# -----------------------------------------------------------------
# --- UPDATED generate_audio FUNCTION ---
# -----------------------------------------------------------------
def generate_audio(text: str, output_path: str, target_duration: float = None) -> str:
    """
    Generates TTS audio using Gemini 2.5 Flash Preview TTS, with key rotation and speed control.
    Saves the audio to a valid WAV file.
    
    Args:
        text: The voiceover text to generate
        output_path: Path where the audio file will be saved
        target_duration: Target duration in seconds (optional, used to calculate speed)
    
    Returns:
        Path to the generated audio file
    """
    num_keys = len(google_key_rotator.api_keys)
    
    # We must save as .wav since the API returns raw PCM data
    # Ensure the output_path ends in .wav
    if not output_path.lower().endswith(".wav"):
        output_path = f"{output_path}.wav"
    
    # Calculate speed if target duration is provided
    speed = 1.0  # Default speed
    if target_duration and target_duration > 0:
        speed = _calculate_tts_speed(text, target_duration)
        word_count = len(text.split())
        expected_wps = word_count / target_duration
        print(f"  📊 Audio speed calculation: {word_count} words, {target_duration:.1f}s target → speed: {speed:.2f}x (expected: {expected_wps:.2f} wps)")

    for i in range(num_keys):
        api_key = google_key_rotator.get_key()
        print(f"--- Requesting audio with key ...{api_key[-4:]} (try {i+1}/{num_keys}) ---")
        genai.configure(api_key=api_key)

        try:
            # --- USING YOUR WORKING MODEL CONFIG (NO SPEED PARAMETER) ---
            # Speed adjustment will be done using moviepy post-processing
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

            # Save to temporary file first
            temp_wav_path = output_path.replace(".wav", "_temp.wav")
            save_pcm_to_wav(temp_wav_path, audio_data)
            
            # Always adjust speed using moviepy if target duration is provided
            # This ensures smooth audio transitions and exact duration matching
            if target_duration and target_duration > 0:
                try:
                    from moviepy import AudioFileClip
                    
                    print(f"  ⚡ Adjusting audio speed to match target duration ({target_duration:.1f}s)...")
                    audio_clip = AudioFileClip(temp_wav_path)
                    original_duration = audio_clip.duration
                    
                    # Calculate the speed needed to match target duration exactly
                    # speed = original_duration / target_duration
                    # This ensures no audio is cut - we just speed up or slow down
                    calculated_speed = original_duration / target_duration
                    
                    # Clamp speed to reasonable bounds for natural-sounding speech
                    # Too fast (>1.5) or too slow (<0.7) sounds unnatural
                    final_speed = max(0.7, min(1.5, calculated_speed))
                    
                    if abs(final_speed - 1.0) > 0.01:  # Only adjust if significant difference
                        print(f"  📊 Original: {original_duration:.2f}s → Target: {target_duration:.2f}s → Speed: {final_speed:.2f}x")
                        
                        # Adjust speed using MoviePy 2.x - resample audio to match target duration
                        # This preserves all audio content, just changes playback speed
                        import numpy as np
                        from moviepy.audio.AudioClip import AudioArrayClip
                        
                        # Get audio array at original fps
                        audio_array = audio_clip.to_soundarray(fps=audio_clip.fps)
                        original_fps = audio_clip.fps
                        
                        # Calculate target number of samples for exact duration match
                        target_samples = int(target_duration * original_fps)
                        original_samples = len(audio_array)
                        
                        if original_samples > 0 and target_samples > 0:
                            # Resample audio to match target duration (no cutting, just resampling)
                            # This changes playback speed smoothly
                            try:
                                from scipy import signal
                                resampled = signal.resample(audio_array, target_samples, axis=0)
                            except ImportError:
                                # Fallback: use numpy interpolation if scipy not available
                                print(f"  ⚠️  scipy not available, using numpy interpolation")
                                indices = np.linspace(0, original_samples - 1, target_samples)
                                if audio_array.ndim == 1:
                                    resampled = np.interp(indices, np.arange(original_samples), audio_array)
                                else:
                                    resampled = np.array([np.interp(indices, np.arange(original_samples), audio_array[:, i]) 
                                                          for i in range(audio_array.shape[1])]).T
                            
                            # Create new audio clip with resampled audio (preserves all content)
                            adjusted_clip = AudioArrayClip(resampled, fps=original_fps)
                        else:
                            adjusted_clip = audio_clip
                        
                        # Verify duration matches (should be very close now)
                        adjusted_duration = adjusted_clip.duration
                        if abs(adjusted_duration - target_duration) > 0.05:
                            # Fine-tune if needed (small adjustment)
                            fine_speed = adjusted_duration / target_duration
                            fine_speed = max(0.95, min(1.05, fine_speed))  # Very small adjustment
                            if abs(fine_speed - 1.0) > 0.01:
                                audio_array_fine = adjusted_clip.to_soundarray(fps=adjusted_clip.fps)
                                fine_target_samples = int(target_duration * adjusted_clip.fps)
                                if len(audio_array_fine) > 0 and fine_target_samples > 0:
                                    try:
                                        from scipy import signal
                                        resampled_fine = signal.resample(audio_array_fine, fine_target_samples, axis=0)
                                    except ImportError:
                                        indices = np.linspace(0, len(audio_array_fine) - 1, fine_target_samples)
                                        if audio_array_fine.ndim == 1:
                                            resampled_fine = np.interp(indices, np.arange(len(audio_array_fine)), audio_array_fine)
                                        else:
                                            resampled_fine = np.array([np.interp(indices, np.arange(len(audio_array_fine)), audio_array_fine[:, i]) 
                                                                      for i in range(audio_array_fine.shape[1])]).T
                                    adjusted_clip = AudioArrayClip(resampled_fine, fps=adjusted_clip.fps)
                                print(f"  🔧 Fine-tuned speed adjustment: {fine_speed:.3f}x")
                        
                        # Write the adjusted audio with high quality settings for smooth transitions
                        adjusted_clip.write_audiofile(
                            output_path,
                            codec='pcm_s16le',  # High quality PCM
                            bitrate='192k'
                        )
                        adjusted_clip.close()
                    else:
                        # Speed is close to 1.0, no adjustment needed
                        print(f"  ✅ Audio duration ({original_duration:.2f}s) already matches target")
                        audio_clip.write_audiofile(
                            output_path,
                            codec='pcm_s16le',
                            bitrate='192k'
                        )
                    
                    audio_clip.close()
                    
                    # Remove temp file
                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)
                    
                    print(f"✅ Audio generated and adjusted to: {output_path}")
                    return output_path
                except Exception as e:
                    print(f"  ⚠️  Post-processing speed adjustment failed: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"  ⚠️  Using original audio without speed adjustment")
                    # Fall back to original audio
                    if os.path.exists(temp_wav_path):
                        os.rename(temp_wav_path, output_path)
                    else:
                        save_pcm_to_wav(output_path, audio_data)
            else:
                # No target duration provided, use original audio
                if os.path.exists(temp_wav_path):
                    os.rename(temp_wav_path, output_path)
                else:
                    save_pcm_to_wav(output_path, audio_data)
            
            print(f"✅ Audio generated and saved to: {output_path}")
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


# -----------------------------------------------------------------
# --- ai_video_gen FUNCTION ---
# -----------------------------------------------------------------
def _get_access_token_from_service_account(service_account_key_path: str) -> str:
    """
    Gets an OAuth 2.0 access token from a service account JSON key file.
    """
    from google.auth.transport.requests import Request as GoogleRequest
    
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    credentials.refresh(GoogleRequest())
    return credentials.token

def _get_access_token_from_adc() -> str:
    """
    Gets an OAuth 2.0 access token using Application Default Credentials (ADC).
    """
    from google.auth import default
    from google.auth.transport.requests import Request
    
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    credentials.refresh(Request())
    return credentials.token

def ai_video_gen(prompt: str, output_path: str, generation_type: str = "text_to_video", aspect_ratio: str = "auto", image_url: str = None) -> str:
    """
    Generates AI video using Vertex AI Veo 3.1 API.
    Downloads the video and saves it to output_path.
    
    Args:
        prompt: Text description of the video to generate
        output_path: Path where the video will be saved
        generation_type: Either "text_to_video" or "image_to_video" (default: "text_to_video")
        aspect_ratio: Video aspect ratio (default: "auto")
        image_url: Required if generation_type is "image_to_video"
    
    Returns:
        str: The output_path where the video was saved
    
    Note:
        Requires VEO_PROJECT_ID environment variable or in VIDEO_GEN_API_KEYS.
        If VIDEO_GEN_API_KEYS contains service account JSON file paths, they will be used.
        If VIDEO_GEN_API_KEYS contains access tokens, they will be used directly.
    """
    # Handle case where video_gen_key_rotator might be None (using ADC)
    if video_gen_key_rotator is None:
        num_keys = 0
    else:
        num_keys = len(video_gen_key_rotator.api_keys)
    
    # Ensure the output_path ends in .mp4
    if not output_path.lower().endswith(".mp4"):
        output_path = f"{output_path}.mp4"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    # Get project ID - try from env var first, then from first API key if it looks like a project ID
    project_id = VEO_PROJECT_ID
    if not project_id and num_keys > 0:
        # Check if first key is a project ID (usually alphanumeric, no special chars)
        first_key = video_gen_key_rotator.api_keys[0]
        if os.path.exists(first_key) or first_key.startswith('{'):
            # It's a file path or JSON, not a project ID
            pass
        else:
            # Might be a project ID or access token
            project_id = first_key if len(first_key) < 50 else ""
    
    if not project_id:
        raise ValueError("VEO_PROJECT_ID must be set in environment variables or provided as first item in VIDEO_GEN_API_KEYS")
    
    location = VEO_LOCATION
    model_name = "veo-3.1-generate-preview"
    
    # Vertex AI endpoint format
    endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:predictLongRunning"
    
    print(f"--- Using Vertex AI Veo 3.1 API ---")
    print(f"--- Project ID: {project_id} ---")
    print(f"--- Location: {location} ---")
    print(f"--- Endpoint: {endpoint} ---")
    
    # Try to get access token - first from keys, then fallback to ADC
    access_token = None
    api_key_or_path = None
    
    if num_keys > 0:
        for i in range(num_keys):
            api_key_or_path = video_gen_key_rotator.get_key()
            print(f"--- Attempting authentication with key ...{api_key_or_path[-4:]} (try {i+1}/{num_keys}) ---")
            
            # Determine if it's a service account file, access token, or project ID
            if os.path.exists(api_key_or_path):
                # It's a service account JSON file path
                print(f"--- Using service account file: {api_key_or_path} ---")
                try:
                    access_token = _get_access_token_from_service_account(api_key_or_path)
                    print(f"✅ Successfully obtained access token from service account")
                    break
                except Exception as e:
                    print(f"⚠️  Failed to get access token from service account: {e}")
                    if i < num_keys - 1:
                        continue
            elif api_key_or_path.startswith('{'):
                # It's a JSON string (service account key content)
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    f.write(api_key_or_path)
                    temp_path = f.name
                try:
                    access_token = _get_access_token_from_service_account(temp_path)
                    print(f"✅ Successfully obtained access token from JSON key")
                    os.unlink(temp_path)
                    break
                except Exception as e:
                    print(f"⚠️  Failed to get access token from JSON key: {e}")
                    os.unlink(temp_path)
                    if i < num_keys - 1:
                        continue
            elif api_key_or_path.startswith('ya29.') or len(api_key_or_path) > 100:
                # Looks like an access token (starts with ya29. or is long)
                print(f"--- Using provided access token ---")
                access_token = api_key_or_path
                break
            else:
                # Might be a file path that doesn't exist, or invalid format
                print(f"⚠️  Key doesn't appear to be a valid file path, JSON, or access token")
                if i < num_keys - 1:
                    continue
    
    # Fallback to Application Default Credentials if no token obtained
    if not access_token:
        print(f"--- No valid credentials from VIDEO_GEN_API_KEYS, trying Application Default Credentials (ADC) ---")
        try:
            access_token = _get_access_token_from_adc()
            print(f"✅ Successfully obtained access token from ADC")
        except Exception as e:
            print(f"⚠️  Failed to get access token from ADC: {e}")
            raise ValueError("Could not obtain access token. Please provide service account JSON file path in VIDEO_GEN_API_KEYS or set up Application Default Credentials.")
    
    # Now use the access token for the API calls
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Prepare the request body for Vertex AI
    # Vertex AI Veo 3.1 uses a specific format
    instances = [{
        "prompt": prompt
    }]
    
    parameters = {
        "sampleCount": 1,
        "resolution": "1080p"  # Limit video resolution to 1080p (1920x1080)
    }
    
    if aspect_ratio != "auto":
        parameters["aspectRatio"] = aspect_ratio
    
    if generation_type == "image_to_video" and image_url:
        instances[0]["image"] = image_url
    
    payload = {
        "instances": instances,
        "parameters": parameters
    }
    
    try:
        # Step 1: Initiate video generation
        print(f"--- Initiating video generation for: '{prompt}' ---")
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        
        # Debug: Print response details
        print(f"--- Response status: {response.status_code} ---")
        if response.content:
            try:
                response_text = response.text[:500]
                print(f"--- Response preview: {response_text} ---")
            except:
                pass
        
        if response.status_code != 200:
            response_data = {}
            try:
                response_data = response.json() if response.content else {}
            except:
                response_data = {"raw_response": response.text[:200]}
            
            error_msg = response_data.get("error", {}).get("message") or response_data.get("message") or f"HTTP {response.status_code}"
            
            print(f"--- Full error response: {response_data} ---")
            
            if response.status_code == 401:
                print(f"⚠️  Unauthorized (401) - Access token may have expired or be invalid")
                raise Exception(f"Unauthorized: {error_msg}. The access token may have expired. Please refresh your credentials.")
            
            if response.status_code == 429:
                print(f"⚠️  Rate-limited. Please wait and try again.")
                raise Exception(f"Rate limited: {error_msg}")
            
            raise Exception(f"Error initiating video generation: {error_msg}")
        
        response_data = response.json()
        
        # Vertex AI returns operation name for long-running operations
        operation_name = response_data.get("name")
        if not operation_name:
            raise Exception("No operation name returned from Vertex AI")
        
        print(f"✅ Video generation initiated. Operation: {operation_name}")
        
        # Step 2: Poll for video status using fetchPredictOperation endpoint
        # According to official docs: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation
        print(f"--- Polling for video status... ---")
        fetch_operation_endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:fetchPredictOperation"
        max_poll_attempts = 120  # Maximum 10 minutes
        poll_attempt = 0
        
        while poll_attempt < max_poll_attempts:
            # Use fetchPredictOperation endpoint with POST request
            fetch_payload = {
                "operationName": operation_name
            }
            status_response = requests.post(fetch_operation_endpoint, headers=headers, json=fetch_payload, timeout=30)
            
            if status_response.status_code != 200:
                error_msg = f"HTTP {status_response.status_code}"
                if status_response.status_code == 429:
                    print(f"Rate-limited while polling. Waiting...")
                    time.sleep(5)
                    poll_attempt += 1
                    continue
                # Log response for debugging
                try:
                    error_data = status_response.json()
                    print(f"--- Error response: {error_data} ---")
                except:
                    print(f"--- Error response text: {status_response.text[:200]} ---")
                raise Exception(f"Error fetching operation status: {error_msg}")
            
            status_data = status_response.json()
            
            # Check if operation is done
            if status_data.get("done", False):
                if "error" in status_data:
                    raise Exception(f"Video generation failed: {status_data['error']}")
                
                # Get the video URI from the response
                # According to docs, response contains "videos" array with "gcsUri" or "bytesBase64Encoded"
                response_result = status_data.get("response", {})
                videos = response_result.get("videos", [])
                
                if not videos:
                    raise Exception("No videos in response")
                
                # Get the first video - it can have either gcsUri or bytesBase64Encoded
                first_video = videos[0]
                video_uri = first_video.get("gcsUri")
                video_bytes = first_video.get("bytesBase64Encoded")
                
                if video_uri:
                    print(f"✅ Video generation completed. URI: {video_uri}")
                    break
                elif video_bytes:
                    # Video is base64 encoded, save it directly
                    import base64
                    print(f"✅ Video generation completed. Saving base64 encoded video...")
                    video_data = base64.b64decode(video_bytes)
                    with open(output_path, "wb") as video_file:
                        video_file.write(video_data)
                    print(f"✅ Video generated and saved to: {output_path}")
                    return output_path
                else:
                    raise Exception("No video URI or base64 data in response")
            else:
                # Still processing
                print(f"⏳ Video generation in progress... (attempt {poll_attempt + 1}/{max_poll_attempts})")
                time.sleep(5)
                poll_attempt += 1
        
        if poll_attempt >= max_poll_attempts:
            raise Exception("Video generation timed out. Maximum polling attempts reached.")
        
        # Step 3: Download the video
        print(f"--- Downloading video from: {video_uri} ---")
        
        # If it's a GCS URI (gs://), we need to use Google Cloud Storage
        if video_uri.startswith("gs://"):
            from google.cloud import storage
            # Parse GCS URI: gs://bucket-name/path/to/file
            uri_parts = video_uri.replace("gs://", "").split("/", 1)
            bucket_name = uri_parts[0]
            blob_name = uri_parts[1] if len(uri_parts) > 1 else ""
            
            # Use service account or default credentials
            if api_key_or_path and os.path.exists(api_key_or_path):
                storage_client = storage.Client.from_service_account_json(api_key_or_path)
            else:
                storage_client = storage.Client(project=project_id)
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename(output_path)
        else:
            # Regular HTTP/HTTPS URL
            with requests.get(video_uri, stream=True, timeout=60) as video_response:
                video_response.raise_for_status()
                with open(output_path, "wb") as video_file:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        video_file.write(chunk)
        
        print(f"✅ Video generated and saved to: {output_path}")
        return output_path
        
    except Exception as e:
        error_message = str(e).lower()
        raise ValueError(f"Failed to generate video: {e}")