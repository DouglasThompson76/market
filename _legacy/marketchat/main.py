from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from marketchat.engine import MarketChatEngine
from marketchat.agent import MarketChatAgent
import os

app = FastAPI(title="MarketChat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize Engine (Global Instance) ---
SNAPSHOT = "MarketSnapshot_output.csv"
EDGE_FILE = "edge/edges_9_types_2026-03-25_121026.csv"

if not os.path.exists(SNAPSHOT) or not os.path.exists(EDGE_FILE):
    print("Warning: Data files not found. MarketChat will initialize in empty mode.")
    engine = None
    agent = None
else:
    engine = MarketChatEngine(SNAPSHOT, EDGE_FILE)
    agent = MarketChatAgent(engine)

# --- Models ---
class ChatRequest(BaseModel):
    message: str

# --- Endpoints ---
@app.get("/")
async def root():
    return {"status": "MarketChat API is live"}

@app.post("/chat")
async def chat(request: ChatRequest):
    if not agent:
        raise HTTPException(status_code=500, detail="Engine not properly initialized. Check data files.")
    
    response = agent.handle_query(request.message)
    return response

@app.get("/health")
async def health():
    return {"status": "UP", "files": {"snapshot": os.path.exists(SNAPSHOT), "edge": os.path.exists(EDGE_FILE)}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
