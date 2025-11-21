from moviepy import TextClip

def list_fonts():
    try:
        fonts = TextClip.list('font')
        print(f"Found {len(fonts)} fonts.")
        print("First 20 fonts:", fonts[:20])
        
        # Check for Arial variants
        arial_fonts = [f for f in fonts if 'arial' in f.lower()]
        print("\nArial variants:", arial_fonts)
        
    except Exception as e:
        print(f"Error listing fonts: {e}")

if __name__ == "__main__":
    list_fonts()
