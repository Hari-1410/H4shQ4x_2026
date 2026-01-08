from fastapi import FastAPI, HTTPException
import networkx as nx

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(payload: dict):
    # ------------------------
    # VALIDATION
    # ------------------------
    if "transactions" not in payload:
        raise HTTPException(status_code=400, detail="transactions field missing")

    transactions = payload["transactions"]

    if not isinstance(transactions, list) or len(transactions) == 0:
        raise HTTPException(
            status_code=400,
            detail="transactions must be a non-empty list"
        )

    # ------------------------
    # BUILD GRAPH
    # ------------------------
    G = nx.DiGraph()

    for tx in transactions:
        if not all(k in tx for k in ("from", "to", "amount")):
            raise HTTPException(
                status_code=400,
                detail="invalid transaction format"
            )
        G.add_edge(tx["from"], tx["to"])

    # ------------------------
    # METRICS
    # ------------------------
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    unique_senders = len({u for u, v in G.edges()})
    unique_receivers = len({v for u, v in G.edges()})

    max_in = max(in_deg.values())
    max_out = max(out_deg.values())

    cycle_present = len(list(nx.simple_cycles(G))) > 0

    # ------------------------
    # RISK LOGIC
    # ------------------------
    risk_score = 0.0
    flags = []

    if unique_senders >= 3:
        risk_score += 0.3
        flags.append("high_sender_diversity")

    if max_out >= 2:
        risk_score += 0.25
        flags.append("rapid_forwarding")

    if cycle_present:
        risk_score += 0.35
        flags.append("cycle_detected")

    risk_score = min(risk_score, 1.0)

    if risk_score >= 0.7:
        risk_level = "HIGH"
    elif risk_score >= 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "flags": flags,
        "metrics": {
            "unique_senders": unique_senders,
            "unique_receivers": unique_receivers,
            "max_in_degree": max_in,
            "max_out_degree": max_out,
            "cycle_present": cycle_present
        }
    }