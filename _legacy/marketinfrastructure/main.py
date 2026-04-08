from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from marketinfrastructure.data_core import InfrastructureDataCore
import os

app = FastAPI(title="MarketInfrastructure API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize Core ---
SNAPSHOT_ROOT = "snapshot"
ROOT_CSV = "MarketSnapshot_output.csv"

if not os.path.exists(ROOT_CSV):
    print("Warning: Infrastructure root data not found.")
    core = None
else:
    core = InfrastructureDataCore(SNAPSHOT_ROOT, ROOT_CSV)

# --- Models ---
class Candidate(BaseModel):
    ticker: str
    gnn_prob: float
    trading_action: str
    resistance_20d: float
    avg_vol_5d: float
    golden_hour_status: str = "PENDING"
    golden_hour_result: Optional[Dict] = None

class ConfirmationPayload(BaseModel):
    symbol: str
    trade_date: str
    passed_orb: bool
    trigger_time_et: str
    trigger_price: float
    vwap_confirm: bool

# --- In-Memory State for Confirmation ---
confirmed_alerts = {} # {symbol: payload}

# --- Endpoints ---
@app.get("/candidates")
async def get_candidates():
    if not core:
        raise HTTPException(status_code=500, detail="Data core not initialized.")
    
    # 1. Generate structural candidates
    cands_df = core.generate_candidates().head(20) # Top 20 for the UI
    symbols = cands_df['ticker'].tolist()
    
    # 2. Enrich with historical metrics
    metrics_df = core.compute_historical_metrics(symbols)
    
    # 3. Merge and add Golden Hour status
    results = []
    for _, row in cands_df.iterrows():
        symbol = row['ticker']
        # Find metrics
        m = metrics_df[metrics_df['ticker'] == symbol]
        res_20d = m['resistance_20d'].iloc[0] if not m.empty else 0
        vol_5d = m['avg_volume_5d'].iloc[0] if not m.empty else 0
        
        # Check for external confirmation
        status = "PENDING"
        payload = None
        if symbol in confirmed_alerts:
            status = "CONFIRMED" if confirmed_alerts[symbol].passed_orb else "FAILED"
            payload = confirmed_alerts[symbol]

        results.append({
            "ticker": symbol,
            "gnn_prob": row['gnn_prob'],
            "trading_action": row['trading_action'],
            "resistance_20d": res_20d,
            "avg_vol_5d": vol_5d,
            "golden_hour_status": status,
            "golden_hour_result": payload
        })
        
    return results

@app.post("/confirm")
async def confirm_alert(payload: ConfirmationPayload):
    """
    Receives signal confirmation from the external minute-data system.
    """
    confirmed_alerts[payload.symbol] = payload
    return {"message": f"Confirmation received for {payload.symbol}", "status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
