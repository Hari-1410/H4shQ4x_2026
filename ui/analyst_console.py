import streamlit as st
import requests
import json
import networkx as nx
import plotly.graph_objects as go
from collections import Counter

API_URL = "http://api:8000/analyze"
API_KEY = "H4shQ4x-2026-SECRET-KEY"

st.set_page_config(page_title="Fraud Risk Analyst Console", layout="wide")

st.markdown("## 🏦 Fraud Risk Analyst Console")
st.caption("Decision-support system")
st.divider()

# -----------------------------
# Input
# -----------------------------
left, right = st.columns([2, 1])

sample = {
    "transactions": [
        {"sender": "L1", "receiver": "MULE", "amount": 9000, "time": "2024-01-01T10:00:00"},
        {"sender": "L1", "receiver": "MULE", "amount": 9000, "time": "2024-01-01T10:05:00"},
        {"sender": "L2", "receiver": "MULE", "amount": 9000, "time": "2024-01-01T10:10:00"},
        {"sender": "MULE", "receiver": "BOSS", "amount": 27000, "time": "2024-01-01T10:20:00"}
    ]
}

with left:
    st.subheader("📥 Transactions")
    raw = st.text_area("JSON Batch", json.dumps(sample, indent=2), height=260)
    run = st.button("🚀 Analyze Batch")

if run:
    payload = json.loads(raw)
    res = requests.post(
        API_URL,
        json=payload,
        headers={"X-API-Key": API_KEY},
        timeout=10
    )
    if res.status_code != 200:
        st.error(res.text)
        st.stop()
    st.session_state.data = res.json()

if "data" not in st.session_state:
    st.info("Paste transactions and run analysis.")
    st.stop()

data = st.session_state.data

with right:
    st.subheader("🧠 Batch Verdict")
    st.metric("Risk Level", data["batch_risk_level"])
    st.metric("Risk Score", f"{data['batch_risk_score']:.2f}")

# -----------------------------
# Tables + Graph
# -----------------------------
st.divider()
table_col, graph_col = st.columns([3, 2])

with table_col:
    tab1, tab2 = st.tabs(["🚩 Accounts", "🔎 Transactions"])
    with tab1:
        st.dataframe(data["accounts"], use_container_width=True)
    with tab2:
        st.dataframe(data["transaction_risks"], use_container_width=True)

with graph_col:
    st.subheader("🌐 Transaction Graph")

    G = nx.MultiDiGraph()
    edge_counter = Counter()

    for tx in data["transactions"]:
        G.add_edge(tx["sender"], tx["receiver"])
        edge_counter[(tx["sender"], tx["receiver"])] += 1

    pos = nx.spring_layout(G, seed=42)
    risk_map = {a["account"]: a["risk_score"] for a in data["accounts"]}

    fig = go.Figure()

    for (u, v), count in edge_counter.items():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        fig.add_trace(go.Scatter(
            x=[x0, x1],
            y=[y0, y1],
            mode="lines",
            line=dict(width=1 + count * 1.5, color="rgba(150,150,150,0.6)"),
            hoverinfo="text",
            text=f"{count} txs"
        ))

    node_x, node_y, colors = [], [], []

    for node, (x, y) in pos.items():
        node_x.append(x)
        node_y.append(y)
        r = risk_map.get(node, 0)
        colors.append("red" if r >= 0.7 else "orange" if r >= 0.4 else "blue")

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(size=18, color=colors),
        text=list(pos.keys()),
        textposition="top center"
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )

    st.plotly_chart(fig, use_container_width=True)
