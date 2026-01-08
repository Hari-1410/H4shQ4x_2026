import streamlit as st
import requests
import json
import networkx as nx
import plotly.graph_objects as go

API_URL = "http://api:8000/analyze"

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Fraud Risk Analyst Console",
    layout="wide"
)

# -----------------------------
# Header
# -----------------------------
st.markdown("## 🏦 Fraud Risk Analyst Console")
st.caption(
    "Internal decision-support system for evaluating transaction batches. "
    "This tool assists analysts; it does not make enforcement decisions."
)

st.divider()

# -----------------------------
# Input
# -----------------------------
st.subheader("📥 Transaction Batch Input")

sample = {
    "transactions": [
        {"sender": "U1", "receiver": "M1", "amount": 5000, "time": "2024-01-01T10:00:00"},
        {"sender": "U2", "receiver": "M1", "amount": 4950, "time": "2024-01-01T10:01:00"},
        {"sender": "M1", "receiver": "R1", "amount": 4920, "time": "2024-01-01T10:02:00"},
        {"sender": "R1", "receiver": "M1", "amount": 4900, "time": "2024-01-01T10:03:00"}
    ]
}

raw_input = st.text_area(
    "Paste structured transaction JSON",
    json.dumps(sample, indent=2),
    height=280
)

if not st.button("Analyze"):
    st.stop()

try:
    payload = json.loads(raw_input)
except Exception:
    st.error("Invalid JSON")
    st.stop()

# -----------------------------
# API call
# -----------------------------
with st.spinner("Analyzing transaction batch..."):
    res = requests.post(API_URL, json=payload)

if res.status_code != 200:
    st.error("Backend analysis failed")
    st.stop()

data = res.json()

# -----------------------------
# Batch decision
# -----------------------------
st.divider()
st.subheader("🧠 Batch Decision")

c1, c2 = st.columns(2)
c1.metric("Risk Level", data["batch_risk_level"])
c2.metric("Risk Score", f'{data["batch_risk_score"]:.2f}')

# -----------------------------
# Explainability Layer (Enterprise)
# -----------------------------
st.divider()
st.subheader("🧠 Explainability Layer")

exp = data["explainability"]

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔍 What this system analyzes")
    for item in exp["data_usage"]:
        st.markdown(f"- {item}")

    st.markdown("### 🧩 Risk signals used")
    for signal in exp["signals_used"]:
        st.markdown(f"- {signal}")

with col2:
    st.markdown("### 📊 Scoring characteristics")
    for s in exp["scoring_characteristics"]:
        st.markdown(f"- {s}")

    st.markdown("### ⚠️ Known limitations")
    for l in exp["limitations"]:
        st.markdown(f"- {l}")

st.markdown("### 🏛️ Intended use")
st.info(exp["intended_use"])

# -----------------------------
# Mule table
# -----------------------------
st.divider()
st.subheader("🚩 Suspicious (Mule-like) Accounts")

accounts = data["accounts"]

if not accounts:
    st.success("No mule-like accounts detected.")
else:
    st.dataframe(
        [
            {
                "Account": a["account"],
                "Incoming": a["incoming"],
                "Outgoing": a["outgoing"],
                "Raw Score": a["raw_score"],
                "Risk Score": a["risk_score"]
            }
            for a in accounts
        ],
        use_container_width=True
    )

# -----------------------------
# Account-level explainability
# -----------------------------
st.divider()
st.subheader("🧾 Account-Level Explainability")


# -----------------------------
# Transaction-level risk
# -----------------------------
st.divider()
st.subheader("🔎 Transaction-Level Risk")

st.dataframe(
    [
        {
            "Sender": t["sender"],
            "Receiver": t["receiver"],
            "Amount": t["amount"],
            "Risk Score": t["risk_score"],
            "Reason": t["reason"]
        }
        for t in data["transaction_risks"]
    ],
    use_container_width=True
)

# -----------------------------
# Graph (context view)
# -----------------------------
st.divider()
st.subheader("🌐 Transaction Graph (Context View)")

G = nx.DiGraph()
for tx in data["transactions"]:
    G.add_edge(tx["sender"], tx["receiver"])

pos = nx.spring_layout(G, seed=42)

mule_map = {a["account"]: a["risk_score"] for a in accounts}

node_x, node_y, node_size, node_color, hover = [], [], [], [], []

for n, (x, y) in pos.items():
    node_x.append(x)
    node_y.append(y)

    degree = G.degree(n)
    node_size.append(16 + degree * 6)

    risk = mule_map.get(n, 0)
    if risk >= 0.7:
        node_color.append("red")
    elif risk >= 0.4:
        node_color.append("orange")
    else:
        node_color.append("blue")

    hover.append(
        f"Account: {n}<br>"
        f"Incoming: {G.in_degree(n)}<br>"
        f"Outgoing: {G.out_degree(n)}<br>"
        f"Risk Score: {risk:.2f}"
    )

edge_x, edge_y = [], []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(color="rgba(150,150,150,0.4)", width=1),
        hoverinfo="none"
    )
)

fig.add_trace(
    go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(width=1, color="white")
        ),
        hovertext=hover,
        hoverinfo="text"
    )
)

fig.update_layout(
    showlegend=False,
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(visible=False),
    yaxis=dict(visible=False)
)

st.plotly_chart(fig, use_container_width=True)
