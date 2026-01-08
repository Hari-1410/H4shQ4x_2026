from fastapi import FastAPI, HTTPException, Header, Depends, Request
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import networkx as nx
import hashlib
import json

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# =========================
# RATE LIMITER SETUP
# =========================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Slow down."}
    )

# =========================
# SECURITY CONFIG
# =========================
API_KEY = "H4shQ4x-2026-SECRET-KEY"

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
# HEALTH CHECK
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# ANALYSIS ENDPOINT (RATE LIMITED)
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
        raise HTTPException(409, "Duplicate batch detected")

    app.state.seen.add(batch_hash)

    # -------------------------
    # Build Graph (Safe)
    # -------------------------
    G = nx.DiGraph()
    for tx in txs:
        G.add_edge(tx.sender, tx.receiver)

    if len(G.nodes) > 200 or len(G.edges) > 500:
        raise HTTPException(413, "Transaction graph too large")

    # -------------------------
    # Detect Cycles (Bounded)
    # -------------------------
    cycle_nodes = set()
    for cycle in nx.cycle_basis(G.to_undirected()):
        if 3 <= len(cycle) <= 6:
            cycle_nodes.update(cycle)

    # -------------------------
    # Account Risk Scoring
    # -------------------------
    accounts = {}

    for node in G.nodes():
        incoming = G.in_degree(node)
        outgoing = G.out_degree(node)

        raw = 0.0
        reasons = []

        if incoming >= 3:
            raw += 0.4
            reasons.append("fund convergence")

        if incoming > 0 and outgoing > 0:
            raw += 0.3
            reasons.append("pass-through behavior")

        if node in cycle_nodes:
            raw += 0.3
            reasons.append("circular movement detected")

        risk = min(raw, 0.9)

        if risk > 0:
            accounts[node] = {
                "account": node,
                "incoming": incoming,
                "outgoing": outgoing,
                "risk_score": round(risk, 2),
                "explanation": ", ".join(reasons)
            }

    # -------------------------
    # Transaction-Level Risk
    # -------------------------
    risky_accounts = {a["account"] for a in accounts.values()}
    transaction_risks = []

    for tx in txs:
        score = 0.0
        reasons = []

        if tx.sender in risky_accounts or tx.receiver in risky_accounts:
            score = 0.5
            reasons.append("linked to high-risk account")

        transaction_risks.append({
            "sender": tx.sender,
            "receiver": tx.receiver,
            "amount": tx.amount,
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
