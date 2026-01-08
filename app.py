
import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# -------------------------------------------------
# STREAMLIT CONFIG
# -------------------------------------------------
st.set_page_config(page_title="UPI Fraud Detection", layout="wide")
st.title("🔍 UPI Fraud & Mule Account Detection System")

# -------------------------------------------------
# DATASET SELECTION
# -------------------------------------------------
st.markdown("### 📊 Select Dataset")

dataset_choice = st.selectbox(
    "Choose transaction dataset",
    ["Synthetic UPI Data", "PaySim Dataset"]
)

# -------------------------------------------------
# LOAD & NORMALIZE DATA
# -------------------------------------------------
if dataset_choice == "Synthetic UPI Data":
    df = pd.read_csv("data/transactions.csv")
    df["time"] = pd.to_datetime(df["time"], format="%H:%M")

else:
    raw_df = pd.read_csv("data/paysim/paysim.csv")

    df = pd.DataFrame()
    df["sender"] = raw_df["nameOrig"]
    df["receiver"] = raw_df["nameDest"]
    df["amount"] = raw_df["amount"]
    df["time"] = pd.to_datetime(raw_df["step"], unit="m")

    # keep demo fast
    df = df.head(5000)

# -------------------------------------------------
# BUILD TRANSACTION GRAPH (DIRECTED)
# -------------------------------------------------
G = nx.DiGraph()
for _, row in df.iterrows():
    G.add_edge(row["sender"], row["receiver"])

# -------------------------------------------------
# MULE ACCOUNT DETECTION
# -------------------------------------------------
results = []
for node in G.nodes():
    if node.startswith(("A", "C")):  # A = synthetic, C = PaySim
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        risk = in_deg + out_deg

        results.append({
            "account": node,
            "incoming": in_deg,
            "outgoing": out_deg,
            "risk_score": risk
        })

risk_df = pd.DataFrame(results).sort_values(
    by="risk_score", ascending=False
)

# -------------------------------------------------
# FRAUD RING DETECTION
# -------------------------------------------------
UG = nx.Graph()
for _, row in df.iterrows():
    UG.add_edge(row["sender"], row["receiver"])

fraud_rings = []
for comp in nx.connected_components(UG):
    if len(comp) > 3:
        sub = UG.subgraph(comp)
        if sub.number_of_edges() > 4:
            fraud_rings.append({
                "accounts": list(comp),
                "num_accounts": len(comp),
                "internal_transactions": sub.number_of_edges()
            })

# -------------------------------------------------
# DASHBOARD: TRANSACTIONS
# -------------------------------------------------
st.subheader("📄 Transactions")
st.dataframe(df.head(100), use_container_width=True)

# -------------------------------------------------
# SUSPICIOUS ACCOUNTS
# -------------------------------------------------
st.subheader("🚩 Suspicious (Mule-like) Accounts")
st.dataframe(risk_df.head(10), use_container_width=True)

# -------------------------------------------------
# ACCOUNT EXPLANATIONS (TIME-AWARE)
# -------------------------------------------------
st.subheader("🟡 Why were these accounts flagged?")

for _, row in risk_df.head(5).iterrows():
    acc = row["account"]

    incoming = df[df["receiver"] == acc].sort_values("time")
    outgoing = df[df["sender"] == acc].sort_values("time")

    reasons = []

    if row["incoming"] > 3:
        reasons.append(f"received money from {row['incoming']} accounts")
    if row["outgoing"] > 3:
        reasons.append(f"sent money to {row['outgoing']} accounts")

    if not incoming.empty and not outgoing.empty:
        delta = (outgoing.iloc[0]["time"] - incoming.iloc[0]["time"]).total_seconds() / 60
        if 0 <= delta <= 15:
            reasons.append(f"forwarded money within {int(delta)} minutes")

    st.markdown(
        f"**Account `{acc}`** was flagged because it " + " and ".join(reasons) + "."
    )

# -------------------------------------------------
# FRAUD RING EXPLANATIONS
# -------------------------------------------------
st.subheader("🔴 Fraud Rings")

if fraud_rings:
    for i, ring in enumerate(fraud_rings, 1):
        st.markdown(f"### Fraud Ring {i}")
        st.markdown(f"- Accounts: {', '.join(ring['accounts'])}")
        st.markdown(f"- Internal transactions: {ring['internal_transactions']}")
else:
    st.success("No fraud rings detected.")

# -------------------------------------------------
# GLOBAL NETWORK VISUALIZATION
# -------------------------------------------------
st.subheader("🕸️ Transaction Network Overview")

pos = nx.spring_layout(G, seed=42)
edge_x, edge_y = [], []

for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]

edge_trace = go.Scatter(
    x=edge_x,
    y=edge_y,
    mode="lines",
    line=dict(width=0.5, color="#aaa"),
    hoverinfo="none"
)

top_accounts = set(risk_df.head(5)["account"])
node_x, node_y, node_colors = [], [], []

for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    node_colors.append("red" if node in top_accounts else "blue")

node_trace = go.Scatter(
    x=node_x,
    y=node_y,
    mode="markers",
    marker=dict(size=10, color=node_colors),
    hoverinfo="text"
)

fig = go.Figure(data=[edge_trace, node_trace])
st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------
# FRAUD RING ISOLATED VISUALIZATION
# -------------------------------------------------
st.subheader("🔴 Fraud Ring Visualization (Isolated View)")

if fraud_rings:
    idx = st.selectbox(
        "Select Fraud Ring",
        range(len(fraud_rings)),
        format_func=lambda x: f"Fraud Ring {x + 1}"
    )

    ring_accounts = set(fraud_rings[idx]["accounts"])
    ring_graph = nx.DiGraph()

    for u, v in G.edges():
        if u in ring_accounts or v in ring_accounts:
            ring_graph.add_edge(u, v)

    pos = nx.spring_layout(ring_graph, seed=7)
    edge_x, edge_y = [], []

    for u, v in ring_graph.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="none"
    )

    node_x, node_y, colors = [], [], []
    for node in ring_graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        colors.append("red" if node in ring_accounts else "lightgray")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(ring_graph.nodes()),
        textposition="top center",
        marker=dict(size=16, color=colors),
        hoverinfo="text"
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No fraud rings available.")
