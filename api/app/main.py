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


def slow_risk(raw, n):
    if raw <= 0 or n <= 0:
        return 0.0
    return 1 - math.exp(-(raw / math.log1p(n)))


# -----------------------------
# API
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(payload: dict = Body(...)):

    txs = payload.get("transactions")
    if not isinstance(txs, list):
        raise HTTPException(400, "transactions must be a list")

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
                raise HTTPException(400, "invalid transaction format")

        s, r = tx["sender"], tx["receiver"]
        t = parse_time(tx["time"])

        G.add_edge(s, r)
        in_times[r].append(t)
        out_times[s].append(t)
        amounts[r].append(tx["amount"])

    # -----------------------------
    # Detect circular fraud (RINGS)
    # -----------------------------
    cycle_nodes = set()
    for c in nx.simple_cycles(G):
        if len(c) >= 3:
            cycle_nodes.update(c)

    # -----------------------------
    # Account risk scoring
    # -----------------------------
    accounts = {}

    for node in G.nodes():
        incoming = G.in_degree(node)
        outgoing = G.out_degree(node)

        raw = 0.0
        reasons = []

        # Funnel / mule signals
        if incoming >= 3:
            raw += 0.4
            reasons.append("fund convergence")

        if incoming > 0 and outgoing > 0:
            ins = sorted(t for t in in_times[node] if t)
            outs = sorted(t for t in out_times[node] if t)
            if ins and outs and (outs[0] - ins[-1]).total_seconds() < 300:
                raw += 0.4
                reasons.append("rapid pass-through")

        if len(amounts[node]) >= 3:
            if max(amounts[node]) - min(amounts[node]) < 0.1 * max(amounts[node]):
                raw += 0.3
                reasons.append("amount structuring")

        # Base risk (slow growth)
        risk = slow_risk(raw, len(txs))

        # 🔥 HARD OVERRIDE — COLLUSIVE RING
        if node in cycle_nodes:
            risk = max(risk, 0.8)
            reasons.append("circular fund movement")

        if risk > 0:
            accounts[node] = {
                "account": node,
                "incoming": incoming,
                "outgoing": outgoing,
                "risk_score": round(risk, 2),
                "explanation": "Account flagged due to " + ", ".join(reasons)
            }

    # -----------------------------
    # Transaction-level risk
    # -----------------------------
    flagged = set(accounts.keys())
    transaction_risks = []

    for tx in txs:
        score = 0.0
        reason = []

        if tx["sender"] in flagged or tx["receiver"] in flagged:
            score = 0.5
            reason.append("linked to high-risk account")

        transaction_risks.append({
            "sender": tx["sender"],
            "receiver": tx["receiver"],
            "amount": tx["amount"],
            "risk_score": round(score, 2),
            "reason": ", ".join(reason) if reason else "no elevated indicators"
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
        "accounts": list(accounts.values()),
        "transaction_risks": transaction_risks,
        "transactions": txs
    }
