import os
from moviepy import TextClip, ColorClip, CompositeVideoClip, vfx

def test_text_clipping():
    print("Testing TextClip clipping...")
    
    # Parameters from video_service.py
    text = "Testing Subtitle Clipping gjpqy" # Include descenders
    font = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    font_size = 80
    color = 'white'
    stroke_color = 'black'
    stroke_width = 5
    target_width = 1080 # Vertical video width
    size = (int(target_width * 0.9), None)
    
    try:
        # Current implementation: method='caption'
        print(f"Generating 'caption' clip with size={size}...")
        txt_clip_caption = TextClip(
            text=text.upper(),
            font=font,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            size=size,
            method='caption',
            text_align='center'
        )
        txt_clip_caption = txt_clip_caption.with_duration(2)
        
        # Create a background to see the clip clearly
        bg = ColorClip(size=(1080, 300), color=(50, 50, 50), duration=2)
        comp_caption = CompositeVideoClip([bg, txt_clip_caption.with_position('center')])
        comp_caption.save_frame("test_caption.png", t=1)
        print("Saved test_caption.png")
        
        # Proposed fix: method='label' + resize
        print(f"Generating 'label' clip with resize logic...")
        txt_clip_label = TextClip(
            text=text.upper(),
            font=font,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='label', # Let it size itself
            text_align='center'
        )
        
        # Check if text is too wide and resize if needed
        max_width = int(target_width * 0.9)
        print(f"Original width: {txt_clip_label.w}, Max width: {max_width}")
        
        # TEST: Add a margin to prevent stroke clipping
        # Sometimes the label method fits the text exactly, and the stroke (centered on edge) gets clipped
        # Adding a margin should fix this.
        from moviepy.video.fx import Margin
        # Note: In MoviePy 2.x it might be vfx.Margin or clip.with_effects([vfx.Margin(...)])
        # Let's try standard margin
        
        # We'll create two versions: one with resize only, one with margin + resize
        
        # Version 1: Current fix (Resize only)
        txt_clip_v1 = txt_clip_label.copy()
        if txt_clip_v1.w > max_width:
            txt_clip_v1 = txt_clip_v1.with_effects([vfx.Resize(width=max_width)])
        
        comp_v1 = CompositeVideoClip([bg, txt_clip_v1.with_position('center')])
        comp_v1.save_frame("test_clipping_v1.png", t=1)
        print("Saved test_clipping_v1.png (Current Fix)")

        # Version 2: Margin + Resize
        print("Generating version with margin...")
        txt_clip_v2 = txt_clip_label.copy()
        
        # Add margin to accommodate stroke
        # stroke_width is 5, so we need at least 2.5px margin, let's say 10px to be safe
        # In MoviePy 2.0, Margin uses left, right, top, bottom
        # Use opacity=0 for transparency instead of color tuple if possible, or ensure color matches clip
        # For TextClip (RGBA), we need RGBA color or None?
        # Let's try opacity=0
        txt_clip_v2 = txt_clip_v2.with_effects([vfx.Margin(left=10, right=10, top=10, bottom=10, opacity=0)]) 
        
        # Version 3: Text Padding (Spaces + Newlines)
        print("Generating version with text padding...")
        # Add spaces for horizontal padding, newlines for vertical
        # We need to strip the newlines later or center vertically?
        # If we add \n, the text will be centered in a taller box.
        padded_text = f"\n {text.upper()} \n" 
        
        txt_clip_v3 = TextClip(
            text=padded_text,
            font=font,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='label',
            text_align='center'
        )
        
        print(f"Padded width: {txt_clip_v3.w}, Height: {txt_clip_v3.h}")
        
        if txt_clip_v3.w > max_width:
             txt_clip_v3 = txt_clip_v3.with_effects([vfx.Resize(width=max_width)])
             
        comp_v3 = CompositeVideoClip([bg, txt_clip_v3.with_position('center')])
        comp_v3.save_frame("test_clipping_v3.png", t=1)
        print("Saved test_clipping_v3.png (Padding Fix)")
        
    except Exception as e:
        print(f"Error: {e}")
        # Try fallback font if Arial-Bold fails
        if "font" in str(e).lower():
            print("Retrying with Arial...")
            txt_clip_caption = TextClip(
                text=text.upper(),
                font='Arial',
                font_size=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                size=size,
                method='caption',
                text_align='center'
            )
            txt_clip_caption.save_frame("test_caption_fallback.png", t=0)

if __name__ == "__main__":
    test_text_clipping()
