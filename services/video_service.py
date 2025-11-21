# services/video_service.py
import os
from moviepy import (
    VideoFileClip, 
    AudioFileClip,
    CompositeAudioClip,
    concatenate_audioclips, 
    concatenate_videoclips,
    vfx,
    TextClip,
    CompositeVideoClip,
    ColorClip,
)
# Use BASE_TEMP_DIR from config
from config import BASE_TEMP_DIR 
from schemas import ScriptResponse
from . import ai_service, media_service

# --- HELPER FUNCTIONS ---

def zoom_in_effect(clip, zoom_ratio=0.04):
    """
    Applies a subtle zoom-in effect to the clip.
    zoom_ratio: Total zoom amount (e.g., 0.04 means 4% zoom over the clip duration).
    """
    def effect(get_frame, t):
        img = get_frame(t)
        h, w = img.shape[:2]
        
        # Calculate current zoom factor (linear interpolation from 1.0 to 1.0 + zoom_ratio)
        current_zoom = 1.0 + (zoom_ratio * (t / clip.duration))
        
        # Calculate new dimensions
        new_w = int(w / current_zoom)
        new_h = int(h / current_zoom)
        
        # Calculate crop coordinates (center)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        
        # Crop and resize back to original
        # Note: This manual implementation is computationally expensive but works.
        # For better performance in MoviePy 2.x, we should use vfx.Resize if possible,
        # but standard resize doesn't support dynamic zoom easily without custom logic.
        # A simpler approach for MoviePy is to use vfx.scroll or similar, but let's stick to a simple crop-resize if needed.
        # HOWEVER, MoviePy's Resize is better.
        # Let's try a simpler approach: Resize the clip to be slightly larger, then crop the center.
        # Actually, let's use the standard MoviePy way if available, or this manual way.
        # Given performance concerns, let's use a simpler "Resize" effect on the whole clip if possible, 
        # but dynamic zoom requires per-frame processing.
        
        # ALTERNATIVE: Use vfx.Resize with a function
        return vfx.Resize(lambda t: 1.0 + (zoom_ratio * (t / clip.duration))).apply(clip).get_frame(t)

    # The above is complex. Let's use a simpler approximation:
    # Resize the clip to (1+zoom_ratio) size, then crop the center.
    # But we want DYNAMIC zoom.
    # Let's use a standard implementation for dynamic zoom.
    return clip.with_effects([vfx.Resize(lambda t: 1.0 + (zoom_ratio * (t / clip.duration)))])

def apply_color_grading(clip):
    """
    Applies 'viral' color grading: High contrast, slightly lower exposure.
    """
    # Increase contrast (lum_contrast)
    # lum = 0 (no brightness change), contrast = 0.2 (20% increase)
    # contrast_threshold=127 is standard (was contrast_thr in older versions)
    clip = clip.with_effects([vfx.LumContrast(lum=0, contrast=0.3, contrast_threshold=127)])
    
    # Slightly lower exposure/gamma to make it "moody" or "premium"
    # MultiplyColor darkens it slightly (0.9 = 90% brightness)
    clip = clip.with_effects([vfx.MultiplyColor(0.9)])
    
    return clip


def create_video(script: ScriptResponse, task_id: str, orientation: str = "horizontal") -> str:
    """
    Orchestrates the entire video creation process.
    All files are saved inside a directory named after the task_id.
    """
    scene_clips = []
    scene_audio_clips = []
    
    # --- NEW FILE ORGANIZATION ---
    # Create a unique directory for this task's files
    task_dir = os.path.join(BASE_TEMP_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    print(f"Starting video creation for task: {task_id}")
    
    for scene in script.scenes:
        # Use scene number for clear file labeling
        scene_filename = f"scene_{scene.scene_number}"
        
        # 1. Generate Audio with speed control
        #    Files are now saved inside the task_dir
        audio_path = os.path.join(task_dir, f"{scene_filename}.wav")
        
        # Get target duration from script
        target_duration = scene.duration_seconds
        
        print(f"Generating audio for scene {scene.scene_number} (target: {target_duration:.1f}s)...")
        ai_service.generate_audio(scene.voiceover_text, audio_path, target_duration=target_duration)
        
        # 2. Load audio clip (already adjusted to target duration by generate_audio)
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        target_duration = scene.duration_seconds
        
        # Verify audio matches target duration (should be very close after speed adjustment)
        duration_diff = abs(audio_duration - target_duration)
        if duration_diff > 0.1:  # If difference is more than 0.1 seconds
            print(f"  ⚠️  Audio duration ({audio_duration:.2f}s) doesn't match target ({target_duration:.2f}s), fine-tuning...")
            # Fine-tune using resampling (no cutting, smooth transition)
            import numpy as np
            from moviepy.audio.AudioClip import AudioArrayClip
            
            audio_array = audio_clip.to_soundarray(fps=audio_clip.fps)
            target_samples = int(target_duration * audio_clip.fps)
            
            if len(audio_array) > 0 and target_samples > 0:
                try:
                    from scipy import signal
                    resampled = signal.resample(audio_array, target_samples, axis=0)
                except ImportError:
                    # Fallback to numpy interpolation
                    indices = np.linspace(0, len(audio_array) - 1, target_samples)
                    if audio_array.ndim == 1:
                        resampled = np.interp(indices, np.arange(len(audio_array)), audio_array)
                    else:
                        resampled = np.array([np.interp(indices, np.arange(len(audio_array)), audio_array[:, i]) 
                                              for i in range(audio_array.shape[1])]).T
                
                audio_clip = AudioArrayClip(resampled, fps=audio_clip.fps)
                print(f"  🔧 Fine-tuned audio to match target duration")
        
        scene_audio_clips.append(audio_clip)
        scene_duration = target_duration  # Use script's target duration
        
        # 3. Get Media (Stock Video or AI-Generated Video)
        media_path = os.path.join(task_dir, f"{scene_filename}.mp4")
        print(f"Fetching media for scene {scene.scene_number} (source: {scene.media_source}, target duration: {scene_duration}s)...")
        
        if scene.media_source.lower() == "stock":
            # Use stock video from Pexels
            print(f"  → Using stock video with query: '{scene.visual_prompt}' (orientation: {orientation})")
            media_service.get_stock_video(scene.visual_prompt, media_path, orientation=orientation)
        elif scene.media_source.lower() == "ai_generated":
            # Use AI video generation (Veo 3.1)
            print(f"  → Generating AI video with prompt: '{scene.visual_prompt}'")
            
            # Determine aspect ratio for AI generation
            ai_aspect_ratio = "16:9"
            if orientation == "vertical":
                ai_aspect_ratio = "9:16"
                
            ai_service.ai_video_gen(
                prompt=scene.visual_prompt,
                output_path=media_path,
                generation_type="text_to_video",
                aspect_ratio=ai_aspect_ratio
            )
        else:
            raise ValueError(f"Unknown media_source: {scene.media_source}. Must be 'stock' or 'ai_generated'.")
        
        # Load and process the video clip
        video_clip = VideoFileClip(media_path)
        
        # Adjust duration to match exact target duration from script
        if video_clip.duration > scene_duration:
            video_clip = video_clip.subclipped(0, scene_duration)
        else:
            # Loop the video if it's shorter than needed
            clips = []
            duration_accumulated = 0
            while duration_accumulated < scene_duration:
                clips.append(video_clip)
                duration_accumulated += video_clip.duration
            video_clip = concatenate_videoclips(clips).subclipped(0, scene_duration)
        
        # Resize/Crop to target format based on orientation
        target_width = 1920
        target_height = 1080
        
        if orientation == "vertical":
            target_width = 1080
            target_height = 1920
            
        # Smart resizing/cropping logic
        # 1. If aspect ratios match, just resize
        # 2. If source is wider than target (e.g. 16:9 source for 9:16 target), crop center then resize
        # 3. If source is taller than target (unlikely here but possible), crop center then resize
        
        # Calculate aspect ratios
        source_ratio = video_clip.w / video_clip.h
        target_ratio = target_width / target_height
        
        if abs(source_ratio - target_ratio) < 0.01:
            # Ratios match, just resize
            video_clip = video_clip.with_effects([vfx.Resize(height=target_height, width=target_width)])
        else:
            # Ratios mismatch, need to crop then resize
            # We want to fill the target frame (cover)
            
            if source_ratio > target_ratio:
                # Source is wider than target (e.g. 16:9 source, 9:16 target)
                # Crop width to match target ratio
                new_source_width = video_clip.h * target_ratio
                video_clip = video_clip.cropped(
                    x_center=video_clip.w / 2, 
                    y_center=video_clip.h / 2, 
                    width=new_source_width, 
                    height=video_clip.h
                )
            else:
                # Source is taller than target
                # Crop height to match target ratio
                new_source_height = video_clip.w / target_ratio
                video_clip = video_clip.cropped(
                    x_center=video_clip.w / 2, 
                    y_center=video_clip.h / 2, 
                    width=video_clip.w, 
                    height=new_source_height
                )
            
            # Now resize to exact target dimensions
            video_clip = video_clip.with_effects([vfx.Resize(height=target_height, width=target_width)])
        
        # 5. Apply Viral Video Effects (Color & Zoom)
        print(f"  → Applying viral effects (Color Grading & Zoom)...")
        try:
            # Apply Color Grading
            video_clip = apply_color_grading(video_clip)
            
            # Apply Zoom Effect
            video_clip = zoom_in_effect(video_clip, zoom_ratio=0.1) # 10% zoom for dynamic feel
        except Exception as e:
            print(f"  ⚠️  Error applying effects: {e}")

        
        # 4. Add subtitles to the video clip (Karaoke Style / Chunked)
        # Create subtitle clip with the voiceover text
        print(f"  → Adding subtitles for scene {scene.scene_number} (Karaoke Style)...")
        
        subtitle_text = scene.voiceover_text
        words = subtitle_text.split()
        
        # Chunk words into groups of 2-4
        chunks = []
        current_chunk = []
        
        import random
        
        for word in words:
            current_chunk.append(word)
            # Randomly decide chunk size between 2 and 4, or if it's the last word
            target_chunk_size = random.randint(2, 4)
            if len(current_chunk) >= target_chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        # Calculate timing for each chunk
        total_words = len(words)
        chunk_clips = []
        current_time = 0
        
        for chunk in chunks:
            chunk_word_count = len(chunk.split())
            # Proportional duration based on word count
            chunk_duration = (chunk_word_count / total_words) * scene_duration
            
            # Create TextClip for this chunk
            try:
                # Use 'label' method to avoid clipping (let it expand)
                # Then resize if it's too wide
                font_path = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
                if not os.path.exists(font_path):
                    font_path = 'Arial-Bold' # Fallback

                # Add spaces and newlines to text to prevent clipping of strokes/descenders
                # This forces the canvas to be larger than the text glyphs
                padded_text = f"\n {chunk.upper()} \n"

                txt_clip = TextClip(
                    text=padded_text, 
                    font=font_path,
                    font_size=80, # Large text
                    color='white',
                    stroke_color='black',
                    stroke_width=5,
                    method='label', # Auto-size to fit text
                    text_align='center'
                )
            except Exception:
                # Fallback to regular Arial if Bold fails
                padded_text = f"\n {chunk.upper()} \n"
                txt_clip = TextClip(
                    text=padded_text,
                    font='Arial',
                    font_size=80,
                    color='white',
                    stroke_color='black',
                    stroke_width=5,
                    method='label',
                    text_align='center'
                )
            
            # Remove the margin effect as we are using text padding
            # txt_clip = txt_clip.with_effects([vfx.Margin(left=10, right=10, top=10, bottom=10, opacity=0)])
            
            # Check if text is too wide and resize if needed
            max_width = int(target_width * 0.9)
            if txt_clip.w > max_width:
                txt_clip = txt_clip.with_effects([vfx.Resize(width=max_width)])
            
            txt_clip = txt_clip.with_duration(chunk_duration)
            
            # Position: Center of screen (Safe Zone)
            txt_clip = txt_clip.with_position('center')
            
            # Set start time
            txt_clip = txt_clip.with_start(current_time)
            
            chunk_clips.append(txt_clip)
            current_time += chunk_duration
            
        # Composite video with all subtitle chunks
        # Note: We don't need a background box for this style as the stroke is heavy
        final_video_clip = CompositeVideoClip([video_clip] + chunk_clips)
        
        # --- ADD BACKGROUND MUSIC ---
        # Check if script has music keywords
        music_path = None
        if hasattr(script, 'background_music_keywords') and script.background_music_keywords:
            # Use maximum 2-3 keywords, join them into a simple search query
            keywords = script.background_music_keywords[:2]  # Limit to 2 keywords
            search_query = " ".join(keywords)
            print(f"🎵 Looking for background music with keywords: {search_query}")
            
            from services import audio_service
            music_path = audio_service.search_music(search_query, duration=int(final_video_clip.duration))
            
        if music_path and os.path.exists(music_path):
            try:
                print(f"🎵 Adding background music: {music_path}")
                music_clip = AudioFileClip(music_path)
                
                # Loop if too short
                if music_clip.duration < final_video_clip.duration:
                    music_clip = vfx.loop(music_clip, duration=final_video_clip.duration)
                else:
                    music_clip = music_clip.subclipped(0, final_video_clip.duration)
                
                # Lower volume for background (e.g., 15-20%)
                music_clip = music_clip.with_volume_scaled(0.15)
                
                # Combine with voiceover
                final_audio = CompositeAudioClip([final_video_clip.audio, music_clip])
                final_video_clip = final_video_clip.with_audio(final_audio)
                print("✅ Background music added successfully")
            except Exception as e:
                print(f"⚠️  Failed to add background music: {e}")
        else:
            print("⚠️  No background music found or keywords missing.")

        scene_clips.append(final_video_clip)

    # 6. Stitch all scenes together
    print("Concatenating all scenes...")
    final_video = concatenate_videoclips(scene_clips,method="compose")
    final_audio = concatenate_audioclips(scene_audio_clips)

    # 7. Write the final file to the task_dir
    output_path = os.path.join(task_dir, "final_video.mp4")
    output_final_audio_path = os.path.join(task_dir, "final_audio.mp3")
    final_audio.write_audiofile(output_final_audio_path)
    final_video.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='libmp3lame',
        temp_audiofile=os.path.join(task_dir, 'temp-audio.mp3'),
        remove_temp=True,
        audio=output_final_audio_path,
        fps=60 # High framerate for smooth motion
    )
    
    print(f"Final video for {task_id} written to: {output_path}")
    
    # (Optional cleanup: remove intermediate scene files)
    # for scene in script.scenes:
    #    os.remove(os.path.join(task_dir, f"scene_{scene.scene_number}.wav"))
    #    os.remove(os.path.join(task_dir, f"scene_{scene.scene_number}.mp4"))
    
    return output_path