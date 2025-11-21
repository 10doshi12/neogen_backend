import sys
import os

# Add the current directory to sys.path so we can import services
sys.path.append(os.getcwd())

from services.ai_service import generate_script

def test_stock_only_generation():
    print("Testing stock-only script generation...")
    prompt = "A calm morning coffee routine"
    try:
        script = generate_script(prompt, total_duration_seconds=10)
        
        print(f"\nGenerated Script Title: {script.title}")
        print(f"Total Scenes: {len(script.scenes)}")
        
        all_stock = True
        for scene in script.scenes:
            print(f"Scene {scene.scene_number}: {scene.media_source}")
            if scene.media_source.lower() != "stock":
                all_stock = False
                print(f"❌ Error: Scene {scene.scene_number} is NOT stock!")
        
        if all_stock:
            print("\n✅ SUCCESS: All scenes are stock scenes.")
        else:
            print("\n❌ FAILURE: Some scenes are not stock scenes.")
            
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")

if __name__ == "__main__":
    test_stock_only_generation()
