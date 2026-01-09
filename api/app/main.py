from fastapi import FastAPI, HTTPException, Header, Depends, Request
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from collections import defaultdict
import networkx as nx
import hashlib
import json
import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# =========================
# RATE LIMITER
# =========================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"}
    )

# =========================
# SECURITY CONFIG
# =========================
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY not configured")

def require_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# =========================
# INPUT MODELS
# =========================
class Transaction(BaseModel):
    sender: str = Field(min_length=2, max_length=32)
    receiver: str = Field(min_length=2, max_length=32)
    amount: float = Field(gt=0, lt=1_000_000)
    time: datetime

class Batch(BaseModel):
    transactions: List[Transaction] = Field(min_items=1, max_items=300)

# =========================
# HEALTH
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# ANALYSIS ENDPOINT
# =========================
@app.post("/analyze", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
def analyze(request: Request, batch: Batch):

    txs = batch.transactions

    # -------------------------
    # Replay Protection
    # -------------------------
    batch_hash = hashlib.sha256(
        json.dumps(batch.dict(), sort_keys=True, default=str).encode()
    ).hexdigest()

    if not hasattr(app.state, "seen"):
        app.state.seen = set()

    if batch_hash in app.state.seen:
        raise HTTPException(409, "Duplicate batch")

    app.state.seen.add(batch_hash)

    # -------------------------
    # Build EVENT GRAPH
    # -------------------------
    G = nx.MultiDiGraph()

    for tx in txs:
        G.add_edge(
            tx.sender,
            tx.receiver,
            amount=tx.amount,
            time=tx.time
        )

    if len(G.nodes) > 200 or G.number_of_edges() > 1000:
        raise HTTPException(413, "Graph too large")

    # -------------------------
    # Pre-compute features
    # -------------------------
    fan_in_count = defaultdict(int)
    fan_out_count = defaultdict(int)
    fan_in_amount = defaultdict(float)
    fan_in_times = defaultdict(list)

    for u, v, data in G.edges(data=True):
        fan_out_count[u] += 1
        fan_in_count[v] += 1
        fan_in_amount[v] += data["amount"]
        fan_in_times[v].append(data["time"])

    # -------------------------
    # Cycle Detection (Directed)
    # -------------------------
    cycle_nodes = set()
    for cycle in nx.simple_cycles(G):
        if 3 <= len(cycle) <= 6:
            cycle_nodes.update(cycle)

    # -------------------------
    # Account Risk Scoring
    # -------------------------
    accounts = {}

    for node in G.nodes():
        raw = 0.0
        reasons = []

        # Fan-in smurfing
        if fan_in_count[node] >= 3:
            raw += 0.3
            reasons.append("high inbound transaction count")

        # Cumulative volume
        if fan_in_amount[node] >= 25000:
            raw += 0.3
            reasons.append("high cumulative inbound volume")

        # Velocity
        times = sorted(fan_in_times[node])
        if len(times) >= 3:
            delta = (times[-1] - times[0]).total_seconds()
            if delta <= 900:
                raw += 0.3
                reasons.append("rapid inbound transaction velocity")

        # Pass-through behavior
        if fan_in_count[node] > 0 and fan_out_count[node] > 0:
            raw += 0.2
            reasons.append("pass-through account")

        # Cycles
        if node in cycle_nodes:
            raw += 0.2
            reasons.append("circular fund movement")

        risk = min(raw, 0.95)

        if risk > 0:
            accounts[node] = {
                "account": node,
                "incoming_txs": fan_in_count[node],
                "outgoing_txs": fan_out_count[node],
                "inbound_amount": round(fan_in_amount[node], 2),
                "risk_score": round(risk, 2),
                "explanation": ", ".join(reasons)
            }

    # -------------------------
    # Transaction Risk
    # -------------------------
    risky_accounts = {a["account"] for a in accounts.values()}
    transaction_risks = []

    for tx in txs:
        score = 0.0
        reasons = []

        if tx.sender in risky_accounts or tx.receiver in risky_accounts:
            score = 0.5
            reasons.append("linked to risky account")

        transaction_risks.append({
            "sender": tx.sender,
            "receiver": tx.receiver,
            "amount": tx.amount,
            "time": tx.time,
            "risk_score": score,
            "reason": ", ".join(reasons) if reasons else "no elevated indicators"
        })

    # -------------------------
    # Batch Risk
    # -------------------------
    batch_risk = max(
        [a["risk_score"] for a in accounts.values()],
        default=0.0
    )

    batch_level = (
        "HIGH" if batch_risk >= 0.7
        else "MEDIUM" if batch_risk >= 0.4
        else "LOW"
    )

    return {
        "batch_risk_score": round(batch_risk, 2),
        "batch_risk_level": batch_level,
        "accounts": list(accounts.values()),
        "transaction_risks": transaction_risks,
        "transactions": [tx.dict() for tx in txs]
    }
