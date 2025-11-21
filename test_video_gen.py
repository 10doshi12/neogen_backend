# test_video_gen.py
"""
Test script for ai_video_gen function.
This script tests the Veo 3.1 API video generation functionality
and saves the output to a test_output folder.
"""
import os
from services.ai_service import ai_video_gen

def test_ai_video_generation():
    """
    Tests the ai_video_gen function with a sample prompt.
    Output is saved to test_output folder.
    """
    # Create test_output directory if it doesn't exist
    test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
    os.makedirs(test_output_dir, exist_ok=True)
    
    # Test prompt
    test_prompt = "A beautiful sunset over the ocean with waves gently lapping the shore"
    
    # Output path in test_output folder
    output_path = os.path.join(test_output_dir, "test_generated_video.mp4")
    
    print("=" * 60)
    print("Testing ai_video_gen function")
    print("=" * 60)
    print(f"Prompt: {test_prompt}")
    print(f"Output will be saved to: {output_path}")
    print("=" * 60)
    print()
    
    try:
        # Call the ai_video_gen function
        result_path = ai_video_gen(
            prompt=test_prompt,
            output_path=output_path,
            generation_type="text_to_video",
            aspect_ratio="auto"
        )
        
        print()
        print("=" * 60)
        print("✅ Test completed successfully!")
        print(f"Video saved to: {result_path}")
        print("=" * 60)
        
        # Verify the file exists
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"File size: {file_size / (1024 * 1024):.2f} MB")
        else:
            print("⚠️  Warning: File path returned but file not found")
            
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Test failed with error:")
        print(f"Error: {e}")
        print("=" * 60)
        raise

if __name__ == "__main__":
    test_ai_video_generation()

