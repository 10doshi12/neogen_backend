# services/video_service.py
import os
from moviepy import (
    VideoFileClip, 
    AudioFileClip,
    concatenate_audioclips, 
    concatenate_videoclips,
    vfx,
)
# Use BASE_TEMP_DIR from config
from config import BASE_TEMP_DIR 
from schemas import ScriptResponse
from . import ai_service, media_service

def create_video(script: ScriptResponse, task_id: str) -> str:
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
        
        # 1. Generate Audio
        #    Files are now saved inside the task_dir
        audio_path = os.path.join(task_dir, f"{scene_filename}.wav")
        
        print(f"Generating audio for scene {scene.scene_number}...")
        ai_service.generate_audio(scene.voiceover_text, audio_path)
        
        # 2. Load audio and get its exact duration
        audio_clip = AudioFileClip(audio_path)
        scene_audio_clips.append(audio_clip)
        scene_duration = audio_clip.duration
        
        # 3. Get Media (Video or Image)
        media_path = os.path.join(task_dir, f"{scene_filename}.mp4")
        print(f"Fetching media for scene {scene.scene_number}...")
        
        if scene.media_type.lower() == "video":
            media_service.get_stock_video(scene.search_query, media_path)
            
            video_clip = VideoFileClip(media_path)
            
            if video_clip.duration > scene_duration:
                video_clip = video_clip.subclipped(0, scene_duration)
            else:
                clips = []
                duration_accumulated = 0
                while duration_accumulated < scene_duration:
                    clips.append(video_clip)
                    duration_accumulated += video_clip.duration
                video_clip = concatenate_videoclips(clips).subclipped(0, scene_duration)
            video_clip = video_clip.with_effects([vfx.Resize(height=1080, width=1920)])
            final_video_clip = video_clip
        
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
        audio=output_final_audio_path
    )
    
    print(f"Final video for {task_id} written to: {output_path}")
    
    # (Optional cleanup: remove intermediate scene files)
    # for scene in script.scenes:
    #    os.remove(os.path.join(task_dir, f"scene_{scene.scene_number}.wav"))
    #    os.remove(os.path.join(task_dir, f"scene_{scene.scene_number}.mp4"))
    
    return output_path