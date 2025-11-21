import sys
import os
import uuid
from schemas import ScriptResponse, SceneScript

# Add the current directory to sys.path so we can import services
sys.path.append(os.getcwd())

from services.video_service import create_video

def test_orientation():
    print("Testing video generation with orientation parameter...")
    
    # Create a dummy script
    script = ScriptResponse(
        title="Test Orientation",
        scenes=[
            SceneScript(
                scene_number=1,
                media_source="stock",
                visual_prompt="nature landscape",
                voiceover_text="This is a test of the vertical orientation.",
                duration_seconds=5.0
            )
        ]
    )
    
    task_id = str(uuid.uuid4())
    print(f"Task ID: {task_id}")
    
    try:
        # Test Vertical
        print("\n--- Testing Vertical Orientation ---")
        video_path_vertical = create_video(script, f"{task_id}_vertical", orientation="vertical")
        print(f"✅ Vertical video created at: {video_path_vertical}")
        
        # Verify dimensions (using MoviePy to check)
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path_vertical)
        print(f"Vertical Video Dimensions: {clip.w}x{clip.h}")
        if clip.w == 1080 and clip.h == 1920:
            print("✅ Dimensions are correct (1080x1920)")
        else:
            print(f"❌ Dimensions are INCORRECT (Expected 1080x1920)")
        clip.close()

        # Test Horizontal
        print("\n--- Testing Horizontal Orientation ---")
        video_path_horizontal = create_video(script, f"{task_id}_horizontal", orientation="horizontal")
        print(f"✅ Horizontal video created at: {video_path_horizontal}")
        
        clip = VideoFileClip(video_path_horizontal)
        print(f"Horizontal Video Dimensions: {clip.w}x{clip.h}")
        if clip.w == 1920 and clip.h == 1080:
            print("✅ Dimensions are correct (1920x1080)")
        else:
            print(f"❌ Dimensions are INCORRECT (Expected 1920x1080)")
        clip.close()
            
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_orientation()
