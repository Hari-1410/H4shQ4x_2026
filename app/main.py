from fastapi import FastAPI, HTTPException
import networkx as nx
import math
from collections import defaultdict
from datetime import datetime

app = FastAPI()

# -----------------------------
# Utility helpers
# -----------------------------

def parse_time(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def sigmoid_like(x):
    # smooth, bounded, never hits 1.0
    return 1 - math.exp(-x)


# -----------------------------
# API
# -----------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(payload: dict):
    if "transactions" not in payload:
        raise HTTPException(status_code=400, detail="transactions missing")

    txs = payload["transactions"]
    if not isinstance(txs, list) or not txs:
        raise HTTPException(status_code=400, detail="transactions must be a non-empty list")

    # -----------------------------
    # Build graph + metadata
    # -----------------------------
    G = nx.DiGraph()
    in_times = defaultdict(list)
    out_times = defaultdict(list)
    amounts = defaultdict(list)

    for tx in txs:
        for k in ("sender", "receiver", "amount", "time"):
            if k not in tx:
                raise HTTPException(status_code=400, detail="invalid transaction format")

        s, r = tx["sender"], tx["receiver"]
        t = parse_time(tx["time"])

        G.add_edge(s, r)
        in_times[r].append(t)
        out_times[s].append(t)
        amounts[r].append(tx["amount"])

    # -----------------------------
    # Detect mule-like accounts
    # -----------------------------
    mule_accounts = {}

    for node in G.nodes():
        incoming = G.in_degree(node)
        outgoing = G.out_degree(node)

        raw_score = 0.0
        reasons = []

        # ---- NEW: score contribution breakdown
        score_breakdown = {
            "convergence": 0.0,
            "rapid_passthrough": 0.0,
            "amount_structuring": 0.0
        }

        convergence = incoming >= 3
        rapid_passthrough = False
        structuring = False

        # Convergence
        if convergence:
            contribution = 0.4
            raw_score += contribution
            score_breakdown["convergence"] = contribution
            reasons.append(f"received funds from {incoming} different accounts")

        # Rapid pass-through
        if incoming > 0 and outgoing > 0:
            in_t = sorted(t for t in in_times[node] if t)
            out_t = sorted(t for t in out_times[node] if t)
            if in_t and out_t and (out_t[0] - in_t[-1]).total_seconds() < 300:
                contribution = 0.4
                raw_score += contribution
                rapid_passthrough = True
                score_breakdown["rapid_passthrough"] = contribution
                reasons.append("forwarded funds shortly after receipt")

        # Amount structuring
        if len(amounts[node]) >= 3:
            if max(amounts[node]) - min(amounts[node]) < 0.1 * max(amounts[node]):
                contribution = 0.3
                raw_score += contribution
                structuring = True
                score_breakdown["amount_structuring"] = contribution
                reasons.append(
                    "handled multiple transactions with unusually similar amounts"
                )

        if raw_score > 0:
            mule_accounts[node] = {
                "incoming": incoming,
                "outgoing": outgoing,
                "raw_score": round(raw_score, 2),
                "risk_score": sigmoid_like(raw_score),
                "risk_factors": {
                    "convergence": convergence,
                    "rapid_passthrough": rapid_passthrough,
                    "amount_structuring": structuring
                },
                "score_breakdown": score_breakdown,  # 👈 NEW
                "explanation": (
                    "Account was flagged because it "
                    + " and ".join(reasons)
                    + "."
                )
            }

    # -----------------------------
    # Transaction-level risk
    # -----------------------------
    mule_set = set(mule_accounts.keys())
    transaction_risks = []

    for tx in txs:
        score = 0.0
        reasons = []

        # NOTE: kept for now (we will fix circularity in STEP 2)
        if tx["sender"] in mule_set or tx["receiver"] in mule_set:
            score += 0.4
            reasons.append("involves mule-like account")

        receiver_amounts = amounts.get(tx["receiver"], [])
        if len(receiver_amounts) >= 2:
            if abs(receiver_amounts[-1] - receiver_amounts[-2]) < 0.1 * receiver_amounts[-1]:
                score += 0.3
                reasons.append("amount similar to adjacent transactions")

        t = parse_time(tx["time"])
        prev_times = in_times.get(tx["receiver"], [])
        if t and prev_times:
            delta = abs((t - prev_times[-1]).total_seconds())
            if delta < 300:
                score += 0.3
                reasons.append("rapid transaction timing")

        score = min(1.0, score)

        transaction_risks.append({
            "sender": tx["sender"],
            "receiver": tx["receiver"],
            "amount": tx["amount"],
            "risk_score": round(score, 2),
            "reason": ", ".join(reasons) if reasons else "no elevated risk indicators"
        })

    # -----------------------------
    # Batch risk (robust aggregation)
    # -----------------------------
    if mule_accounts:
        risks = [a["risk_score"] for a in mule_accounts.values()]
        batch_risk_score = min(
            1.0,
            0.6 * max(risks) + 0.4 * (sum(risks) / len(risks))
        )
    else:
        batch_risk_score = 0.0

    if batch_risk_score >= 0.7:
        batch_risk_level = "HIGH"
    elif batch_risk_score >= 0.4:
        batch_risk_level = "MEDIUM"
    else:
        batch_risk_level = "LOW"

    # -----------------------------
    # Explainability Layer (Enterprise)
    # -----------------------------
    explainability_layer = {
        "model_type": "Rule-based graph risk engine",
        "data_usage": [
            "Transaction sender and receiver relationships",
            "Transaction timestamps",
            "Transaction amounts"
        ],
        "signals_used": [
            "Account convergence (many-to-one fund flows)",
            "Rapid pass-through behavior",
            "Transaction amount structuring"
        ],
        "scoring_characteristics": [
            "Bounded risk scores between 0 and 1",
            "Monotonic scoring (additional risk signals never reduce risk)",
            "No historical customer profiling"
        ],
        "limitations": [
            "Operates on transaction batches, not live streams",
            "Does not infer intent, identity, or criminality",
            "Thresholds are heuristic and configurable"
        ],
        "intended_use": (
            "Decision-support system for human analysts. "
            "Outputs should be interpreted alongside additional investigative context."
        )
    }

    # -----------------------------
    # Response
    # -----------------------------
    return {
        "batch_risk_score": round(batch_risk_score, 2),
        "batch_risk_level": batch_risk_level,
        "explainability": explainability_layer,
        "accounts": [
            {
                "account": acc,
                "incoming": info["incoming"],
                "outgoing": info["outgoing"],
                "raw_score": info["raw_score"],
                "risk_score": round(info["risk_score"], 2),
                "risk_factors": info["risk_factors"],
                "score_breakdown": info["score_breakdown"],  # 👈 NEW
                "explanation": info["explanation"]
            }
            for acc, info in mule_accounts.items()
        ],
        "transaction_risks": transaction_risks,
        "transactions": txs
    }
