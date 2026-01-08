import pandas as pd
import networkx as nx

# load data
df = pd.read_csv("data/transactions.csv")

# build directed graph (accounts only)
G = nx.DiGraph()

for _, row in df.iterrows():
    sender = row["sender"]
    receiver = row["receiver"]
    G.add_edge(sender, receiver)

results = []

for node in G.nodes():
    # consider only account nodes
    if node.startswith("A"):
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)

        # mule-like logic
        risk_score = in_deg + out_deg

        results.append({
            "account": node,
            "incoming": in_deg,
            "outgoing": out_deg,
            "risk_score": risk_score
        })

risk_df = pd.DataFrame(results)

# sort by risk
risk_df = risk_df.sort_values(by="risk_score", ascending=False)
risk_df = risk_df[risk_df["incoming"] > 3]


print("🔴 Top suspicious (mule-like) accounts:")
print(risk_df.head(10))

print("\n🟠 Detecting potential fraud rings...")

# build undirected graph (accounts only)
UG = nx.Graph()

for _, row in df.iterrows():
    sender = row["sender"]
    receiver = row["receiver"]
    UG.add_edge(sender, receiver)

# find connected components (groups)
components = list(nx.connected_components(UG))

fraud_rings = []

for comp in components:
    if len(comp) > 2:
        subgraph = UG.subgraph(comp)
        edge_count = subgraph.number_of_edges()

        if len(comp) > 3 and edge_count > 4:
            fraud_rings.append({
                "accounts": list(comp),
                "num_accounts": len(comp),
                "internal_transactions": edge_count
            })


# show detected rings
if fraud_rings:
    print("🔴 Potential Fraud Rings Detected:\n")
    for i, ring in enumerate(fraud_rings, 1):
        print(f"Ring {i}:")
        print(" Accounts:", ring["accounts"])
        print(" Number of accounts:", ring["num_accounts"])
        print(" Internal transactions:", ring["internal_transactions"])
        print("-" * 40)
else:
    print("✅ No fraud rings detected.")

    
print("\n🟡 EXPLANATIONS FOR FLAGGED ACCOUNTS:\n")

for _, row in risk_df.head(5).iterrows():
    reasons = []

    if row["incoming"] > 3:
        reasons.append(f"received money from {row['incoming']} different accounts")

    if row["outgoing"] > 3:
        reasons.append(f"sent money to {row['outgoing']} different accounts")

    explanation = " and ".join(reasons)

    print(f"Account {row['account']} was flagged because it {explanation}.")
