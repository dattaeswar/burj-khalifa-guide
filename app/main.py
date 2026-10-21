"""
app/main.py - FastAPI application for Burj Khalifa Guide chatbot.
Exposes:
- GET /api/health
- POST /api/chat (SSE streaming)
- GET /api/chunks
- Serves static assets and index.html
"""

import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.knowledge import kb_manager
from app.llm import stream_chat_completion

# Configure logging (ensuring API keys are never logged)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("burj_guide.main")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Burj Khalifa Guide",
    description="A factual AI chatbot about the construction of Burj Khalifa powered by DeepSeek.",
    version="1.0.0"
)

# Enable CORS for convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)


@app.get("/api/health")
async def health_check():
    """Returns the operational status and whether the knowledge base is loaded."""
    is_loaded = kb_manager.is_loaded
    chunks = kb_manager.get_chunks()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    has_api_key = bool(os.getenv("DEEPSEEK_API_KEY", "").strip()) and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here"

    return {
        "status": "ok" if is_loaded else "degraded",
        "knowledge_base_loaded": is_loaded,
        "sections_count": len(chunks),
        "model": model,
        "api_key_configured": has_api_key
    }


@app.get("/api/chunks")
async def get_chunks():
    """Returns the section list for UI citations and reference display."""
    return {
        "chunks": [
            {
                "section_number": c["section_number"],
                "title": c["title"]
            }
            for c in kb_manager.get_chunks()
        ]
    }


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Accepts conversation messages, caps input at 1,000 chars, limits history to
    the last 10 turns, and streams back the reply via Server-Sent Events.
    """
    raw_messages = request.messages

    # Check that the last message is from user and does not exceed 1,000 characters
    last_msg = raw_messages[-1]
    if last_msg.role != "user":
        raise HTTPException(status_code=400, detail="The last message must be from the user.")

    if len(last_msg.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if len(last_msg.content) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Input length exceeds the 1,000 character limit. Please shorten your question."
        )

    # Limit history to the last 10 turns (up to 10 messages)
    truncated_messages = [
        {"role": m.role, "content": m.content[:1000]}
        for m in raw_messages[-10:]
    ]

    # Ensure system prompt is loaded
    system_prompt = kb_manager.get_system_prompt()
    if not system_prompt:
        return JSONResponse(
            status_code=500,
            content={"error": "Knowledge base not ready. Please verify ingest.py has been run."}
        )

    return StreamingResponse(
        stream_chat_completion(truncated_messages, system_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Mount static files and serve index.html
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"error": "index.html not found"})
