from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import os

from core.daily_edge import DailyEdgeService
from core.engine import UnifiedMarketEngine
from core.agent import UnifiedMarketAgent

app = FastAPI(title="Market Intelligence Suite", version="1.1.0")

# --- Security: CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Shared Engine Initialization ---
SNAPSHOT_ROOT = "snapshot"
ROOT_CSV = "MarketSnapshot_output.csv"
EDGE_FILE = "edge/edges_9_types_2026-03-25_121026.csv"

if os.path.exists(ROOT_CSV) and os.path.exists(EDGE_FILE):
    engine = UnifiedMarketEngine(SNAPSHOT_ROOT, ROOT_CSV, EDGE_FILE)
    agent = UnifiedMarketAgent(engine)
else:
    print("Warning: Chat engine data files not found.")
    engine = None
    agent = None

if os.path.exists(ROOT_CSV) and os.path.exists(SNAPSHOT_ROOT):
    edge_service = DailyEdgeService(os.getcwd())
else:
    print("Warning: Daily edge service data files not found.")
    edge_service = None

# --- Models ---
class ChatRequest(BaseModel):
    message: str

class ConfirmationPayload(BaseModel):
    symbol: str
    trade_date: str
    passed_orb: bool
    trigger_time_et: str
    trigger_price: float
    vwap_confirm: bool

# --- State ---
confirmed_alerts = {}

# --- API Endpoints ---
@app.get("/api/health")
async def health():
    return {
        "status": "UP",
        "engine": engine is not None,
        "daily_edge": edge_service is not None,
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not agent: raise HTTPException(status_code=500, detail="Agent not ready.")
    return agent.handle_query(request.message)

@app.get("/api/candidates")
async def get_candidates():
    if not edge_service:
        raise HTTPException(status_code=500, detail="Daily edge service not ready.")
    return [candidate.to_dict() for candidate in edge_service.list_candidates(limit=150)]

@app.post("/api/confirm")
async def confirm_alert(payload: ConfirmationPayload):
    confirmed_alerts[payload.symbol.upper()] = payload
    return {"status": "OK", "symbol": payload.symbol}

# --- Static UI Serving ---
@app.get("/")
async def serve_ui():
    return FileResponse("interface/index.html")

# Mount interface directory for CSS/JS if needed
# app.mount("/static", StaticFiles(directory="interface"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
