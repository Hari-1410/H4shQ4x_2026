from fastapi import FastAPI, HTTPException, Body
import networkx as nx
import math
from collections import defaultdict
from datetime import datetime

app = FastAPI()

# -----------------------------
# Helpers
# -----------------------------

def parse_time(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def scaled_risk(raw_score: float, batch_size: int) -> float:
    if raw_score <= 0 or batch_size <= 0:
        return 0.0
    scale = math.log1p(batch_size)
    return 1 - math.exp(-(raw_score / scale))


# -----------------------------
# API
# -----------------------------

@app.post("/analyze")
def analyze(payload: dict = Body(...)):

    txs = payload.get("transactions")
    if not isinstance(txs, list):
        raise HTTPException(status_code=400, detail="transactions must be a list")

    if len(txs) == 0:
        return {
            "batch_risk_score": 0.0,
            "batch_risk_level": "LOW",
            "accounts": [],
            "transaction_risks": [],
            "transactions": []
        }

    # -----------------------------
    # Build graph
    # -----------------------------
    G = nx.DiGraph()
    in_times = defaultdict(list)
    out_times = defaultdict(list)
    amounts = defaultdict(list)

    for tx in txs:
        for k in ("sender", "receiver", "amount", "time"):
            if k not in tx:
                raise HTTPException(status_code=400, detail="invalid transaction")

        s, r = tx["sender"], tx["receiver"]
        t = parse_time(tx["time"])

        G.add_edge(s, r)
        in_times[r].append(t)
        out_times[s].append(t)
        amounts[r].append(tx["amount"])

    # -----------------------------
    # Detect cycles (ring fraud)
    # -----------------------------
    cycle_nodes = set()
    for c in nx.simple_cycles(G):
        if len(c) >= 3:
            cycle_nodes.update(c)

    # -----------------------------
    # Account risk
    # -----------------------------
    accounts = {}

    for node in G.nodes():
        incoming = G.in_degree(node)
        outgoing = G.out_degree(node)

        raw_score = 0.0
        reasons = []

        # Mule patterns
        if incoming >= 3:
            raw_score += 0.4
            reasons.append(f"received funds from {incoming} accounts")

        if incoming > 0 and outgoing > 0:
            ins = sorted(t for t in in_times[node] if t)
            outs = sorted(t for t in out_times[node] if t)
            if ins and outs and (outs[0] - ins[-1]).total_seconds() < 300:
                raw_score += 0.4
                reasons.append("rapid pass-through behavior")

        if len(amounts[node]) >= 3:
            if max(amounts[node]) - min(amounts[node]) < 0.1 * max(amounts[node]):
                raw_score += 0.3
                reasons.append("structured transaction amounts")

        # Base risk
        risk = scaled_risk(raw_score, len(txs))

        # 🔥 HARD OVERRIDE: CIRCULAR FRAUD
        if node in cycle_nodes:
            risk = max(risk, 0.75)
            reasons.append("participates in circular fund movement")

        if risk > 0:
            accounts[node] = {
                "incoming": incoming,
                "outgoing": outgoing,
                "risk_score": round(risk, 2),
                "explanation": "Account flagged because it " + " and ".join(reasons) + "."
            }

    # -----------------------------
    # Transaction-level risk (simple)
    # -----------------------------
    flagged = set(accounts.keys())
    transaction_risks = []

    for tx in txs:
        score = 0.0
        reasons = []

        if tx["sender"] in flagged or tx["receiver"] in flagged:
            score += 0.5
            reasons.append("linked to high-risk account")

        transaction_risks.append({
            "sender": tx["sender"],
            "receiver": tx["receiver"],
            "amount": tx["amount"],
            "risk_score": round(min(score, 1.0), 2),
            "reason": ", ".join(reasons) if reasons else "no elevated indicators"
        })

    # -----------------------------
    # Batch risk = strongest signal
    # -----------------------------
    if accounts:
        batch_risk_score = max(a["risk_score"] for a in accounts.values())
    else:
        batch_risk_score = 0.0

    batch_risk_level = (
        "HIGH" if batch_risk_score >= 0.7
        else "MEDIUM" if batch_risk_score >= 0.4
        else "LOW"
    )

    return {
        "batch_risk_score": round(batch_risk_score, 2),
        "batch_risk_level": batch_risk_level,
        "accounts": [{"account": k, **v} for k, v in accounts.items()],
        "transaction_risks": transaction_risks,
        "transactions": txs
    }
