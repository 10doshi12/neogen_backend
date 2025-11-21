# main.py
import uuid
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from schemas import VideoRequest
from services import ai_service, video_service
from config import BASE_TEMP_DIR

app = FastAPI(
    title="AI Video Generation API",
    description="Generates a video from a text prompt asynchronously.",
)

# Add CORS middleware to allow requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Task Status "Database" ---
# This global dictionary will store the status of each task.
# In production, you'd replace this with a database (like Redis or Postgres).
task_statuses = {}

# --- The Background Worker Function ---

def run_video_generation(task_id: str, prompt: str, duration_seconds: int = 20, orientation: str = "horizontal"):
    """
    This is the long-running function that runs in the background.
    It updates the task_statuses dictionary as it progresses.
    
    Args:
        task_id: Unique identifier for this video generation task
        prompt: The user's video prompt
        prompt: The user's video prompt
        duration_seconds: The exact total duration for the video (default: 20)
        orientation: Video orientation ("horizontal" or "vertical")
    """
    try:
        # 1. Update status
        task_statuses[task_id] = {"status": "generating_script", "message": f"Generating script for {duration_seconds} second video ({orientation})..."}
        
        # 2. Generate script with the specified duration
        script = ai_service.generate_script(prompt, total_duration_seconds=duration_seconds)
        
        # 3. Update status
        task_statuses[task_id] = {"status": "generating_video", "message": "Script complete. Generating video..."}
        
        # 4. Create video (This is the long part)
        # We pass the task_id to video_service for file organization
        video_path = video_service.create_video(script, task_id, orientation)
        
        # 5. Update status to "complete"
        final_file_path = os.path.relpath(video_path, BASE_TEMP_DIR)
        task_statuses[task_id] = {
            "status": "complete",
            "message": "Video generation complete.",
            "video_filename": final_file_path # e.g., "task_id_xyz/final_video.mp4"
        }

    except Exception as e:
        print(f"--- Task {task_id} FAILED ---")
        print(f"Error: {e}")
        # 6. Update status to "error"
        task_statuses[task_id] = {"status": "error", "message": str(e)}

# --- API Endpoints ---

@app.post("/generate-video")
async def generate_video_endpoint(request: VideoRequest, background_tasks: BackgroundTasks):
    """
    Receives the request, assigns a task_id, and starts the
    video generation in the background. Returns 202 Accepted.
    """
    # 1. Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # 2. Initialize the status for this task
    task_statuses[task_id] = {"status": "pending", "message": "Task received and queued."}
    
    # 3. Add the long-running function to the background task queue
    background_tasks.add_task(
        run_video_generation, 
        task_id, 
        request.prompt,
        request.video_length_seconds,
        request.orientation
    )
    
    # 4. Return immediately with the task_id
    return JSONResponse(
        status_code=202, # "Accepted"
        content={
            "message": "Video generation started. Poll the status endpoint to check progress.",
            "task_id": task_id,
            "status_url": f"/status/{task_id}"
        }
    )

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Poll this endpoint to check the status of a generation task.
    """
    status = task_statuses.get(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task ID not found.")
    
    if status["status"] == "complete":
        # If complete, provide the download URL
        status["download_url"] = f"/download/{status['video_filename']}"
    
    return status

@app.get("/download/{task_id}/{filename}")
async def download_video(task_id: str, filename: str):
    """
    Downloads the final video file.
    The path comes from the status endpoint (e.g., task_id/final_video.mp4).
    """
    file_path = os.path.join(BASE_TEMP_DIR, task_id, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found. It may still be generating or an error occurred.")

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)