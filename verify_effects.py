
from moviepy import vfx, VideoFileClip, ColorClip

def verify_effects():
    print("Verifying MoviePy 2.x effects...")
    
    # Check for LumContrast
    if hasattr(vfx, 'LumContrast') or hasattr(vfx, 'lum_contrast'):
        print("✅ LumContrast/lum_contrast found")
    else:
        print("❌ LumContrast/lum_contrast NOT found")
        
    # Check for Colorx
    if hasattr(vfx, 'Colorx') or hasattr(vfx, 'colorx'):
        print("✅ Colorx/colorx found")
    else:
        print("❌ Colorx/colorx NOT found")
        
    # Check for Resize
    if hasattr(vfx, 'Resize') or hasattr(vfx, 'resize'):
        print("✅ Resize/resize found")
    else:
        print("❌ Resize/resize NOT found")

    try:
        # Create a dummy clip to test effect application
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=1)
        
        # Test Resize
        try:
            clip = clip.with_effects([vfx.Resize(width=50)])
            print("✅ vfx.Resize application successful")
        except Exception as e:
            print(f"❌ vfx.Resize application failed: {e}")

    except Exception as e:
        print(f"❌ Error creating dummy clip: {e}")

if __name__ == "__main__":
    verify_effects()
