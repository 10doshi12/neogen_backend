# schemas.py
from pydantic import BaseModel
from typing import List

class VideoRequest(BaseModel):
    prompt: str
    video_length_seconds: int = 20

class SceneScript(BaseModel):
    scene_number: int
    media_type: str  # "video" or "image"
    search_query: str
    voiceover_text: str
    duration_seconds: float

class ScriptResponse(BaseModel):
    title: str
    scenes: List[SceneScript]