from moviepy import ColorClip, vfx

def test_lum_contrast():
    print("Testing LumContrast...")
    try:
        clip = ColorClip(size=(100, 100), color=(100, 100, 100), duration=1)
        
        # This is the call causing the error
        print("Attempting vfx.LumContrast(lum=0, contrast=0.3, contrast_threshold=127)...")
        clip = clip.with_effects([vfx.LumContrast(lum=0, contrast=0.3, contrast_threshold=127)])
        print("Success!")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Try to inspect the class to see available arguments
        try:
            import inspect
            print("\nLumContrast arguments:")
            print(inspect.signature(vfx.LumContrast.__init__))
        except Exception as inspect_e:
            print(f"Could not inspect LumContrast: {inspect_e}")

if __name__ == "__main__":
    test_lum_contrast()
