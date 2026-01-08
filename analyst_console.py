import streamlit as st
import requests
import json
import networkx as nx
import plotly.graph_objects as go

API_URL = "http://api:8000/analyze"

st.set_page_config(page_title="Fraud Risk Analyst Console", layout="wide")

st.markdown("## 🏦 Fraud Risk Analyst Console")
st.caption("Decision-support system.")
st.divider()

# -----------------------------
# Input
# -----------------------------
left, right = st.columns([2, 1])

sample = {
    "transactions": [
        {"sender": "U1", "receiver": "M1", "amount": 5200, "time": "2024-01-01T11:00:00"},
        {"sender": "U2", "receiver": "M2", "amount": 5100, "time": "2024-01-01T11:01:00"},
        {"sender": "M1", "receiver": "R1", "amount": 5000, "time": "2024-01-01T11:02:00"},
        {"sender": "M2", "receiver": "R1", "amount": 4950, "time": "2024-01-01T11:03:00"},
        {"sender": "R1", "receiver": "M1", "amount": 4900, "time": "2024-01-01T11:04:00"},
        {"sender": "R1", "receiver": "M2", "amount": 4850, "time": "2024-01-01T11:05:00"}
    ]
}

with left:
    st.subheader("📥 Transactions")
    raw = st.text_area("JSON Batch", json.dumps(sample, indent=2), height=240)
    run = st.button("🚀 Analyze Batch")

if run:
    payload = json.loads(raw)
    res = requests.post(API_URL, json=payload)
    if res.status_code != 200:
        st.error(res.text)
        st.stop()
    st.session_state.data = res.json()

if "data" not in st.session_state:
    st.info("Run analysis to see results.")
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

    G = nx.DiGraph()
    for tx in data["transactions"]:
        G.add_edge(tx["sender"], tx["receiver"])

    pos = nx.spring_layout(G, seed=42)
    risk_map = {a["account"]: a["risk_score"] for a in data["accounts"]}

    node_x, node_y, node_color = [], [], []

    for n, (x, y) in pos.items():
        node_x.append(x)
        node_y.append(y)
        r = risk_map.get(n, 0)
        node_color.append("red" if r >= 0.7 else "orange" if r >= 0.4 else "blue")

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(color="rgba(160,160,160,0.4)")))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers",
                             marker=dict(size=18, color=node_color)))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )

    st.plotly_chart(fig, use_container_width=True)
