# schemas.py
from pydantic import BaseModel
from typing import List

class VideoRequest(BaseModel):
    prompt: str
    video_length_seconds: int = 20
    orientation: str = "horizontal"  # "horizontal" or "vertical"

class SceneScript(BaseModel):
    scene_number: int
    media_source: str  # "stock" or "ai_generated"
    visual_prompt: str  # Search query for stock, or detailed description for AI-generated
    voiceover_text: str
    duration_seconds: float

class ScriptResponse(BaseModel):
    title: str
    background_music_keywords: List[str] # Keywords to search for background music
    scenes: List[SceneScript]