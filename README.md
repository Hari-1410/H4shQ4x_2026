# 🏦 Graph-Driven Fraud Detection for UPI Mule Accounts

### Build2Break Hackathon Submission

This project implements a **graph-driven fraud analysis engine** designed to identify **mule accounts and collusive behavior** in UPI-style transaction systems.

The system operates as a **backend fraud decision service**, intended to be integrated with banking or payment infrastructure.
It analyzes transaction relationships using graph-based metrics and returns **explainable risk assessments** to fraud analysts.

> ⚠️ This system is designed for **simulation, adversarial evaluation, and system hardening**, not for real-world financial enforcement.

---

## 🎯 Problem Statement

Mule accounts and collusive transaction rings are difficult to detect using isolated transaction checks.
Individually, transactions may appear legitimate, but **relational patterns** across multiple users often reveal coordinated behavior.

This project addresses that challenge by:

* Modeling transactions as a **graph**
* Extracting **graph-based behavioral signals**
* Converting those signals into **explainable fraud risk indicators**

---

## 🧠 System Overview

The system follows a **decision-support architecture** commonly used in real financial institutions.

**Key idea:**

> Graphs are used as an **analytical tool**, not as the final decision.

The system computes graph metrics internally and produces **explicit risk scores and explanations**, with optional visual evidence for analysts.

---

## 🔁 Real-World Workflow (How This Works in Practice)

1. Users perform UPI transactions
2. Banking systems collect transaction events
3. Transactions are aggregated into structured batches
4. These batches are submitted to the fraud analysis API
5. The API returns a risk score and explainable indicators
6. The bank or fraud analyst decides whether to:

   * Allow the activity
   * Flag it
   * Escalate for review

📌 **End users never interact with this system directly.**

---

## 🧩 Architecture

```
UPI / Payment Systems
        ↓
 Transaction Events (JSON)
        ↓
 Fraud Analysis API (FastAPI)
        ↓
 Risk Score + Explanations
        ↓
 Analyst Decision / Bank Policy
```

An optional **Streamlit Analyst Console** is provided to visualize and inspect results during demonstrations.

---

## 🚀 API Usage

### Health Check

```
GET /health
```

**Response**

```json
{ "status": "ok" }
```

---

### Fraud Analysis Endpoint

```
POST /analyze
```

This endpoint represents the interface through which **bank systems or fraud monitoring pipelines** submit transaction batches for evaluation.

#### Example Input

*(Simulated transaction batch sent by a bank system)*

```json
{
  "transactions": [
    { "from": "U1", "to": "A1", "amount": 5000 },
    { "from": "U2", "to": "A1", "amount": 4800 },
    { "from": "U3", "to": "A1", "amount": 5100 }
  ]
}
```

#### Example Output

```json
{
  "risk_score": 0.82,
  "risk_level": "HIGH",
  "flags": [
    "high_sender_diversity",
    "similar_amounts",
    "cyclic_flow_detected"
  ],
  "metrics": {
    "unique_senders": 3,
    "unique_receivers": 1,
    "in_degree": 3,
    "out_degree": 0,
    "cycle_detected": true
  }
}
```

---

## 📊 Risk Interpretation

* **LOW** → benign behavior
* **MEDIUM** → requires monitoring
* **HIGH** → likely mule or collusive behavior

Each risk decision is accompanied by **explicit reasons** derived from graph metrics.

---

## 🖥️ Analyst Console (Optional UI)

A minimal **Streamlit-based analyst console** is included for:

* Demonstration
* Inspection
* Explanation of decisions

The UI:

* Accepts structured transaction input
* Calls the fraud analysis API
* Displays risk scores, metrics, and optional graph evidence

⚠️ **All fraud logic resides in the API, not in the UI.**

---

## 🛠️ Running the System

### Prerequisites

* Docker
* Docker Compose

### Steps

```bash
git clone <repo-url>
cd <repo-name>
docker compose up
```

* API available at: `http://localhost:8000`
* Analyst UI (if enabled): `http://localhost:8501`

---

## 🧪 Break Phase & Adversarial Testing

For the Build2Break hackathon:

* Breaking teams interact with the system via the **API**
* Breakers simulate **bank systems or fraud analysts**
* Inputs are provided as structured JSON payloads

This enables reproducible, systematic testing of:

* Threshold logic
* Graph assumptions
* Edge cases

---

## ⚠️ Assumptions & Limitations

* The system operates on **transaction batches**, not live streams
* Time relationships are approximated
* Thresholds are heuristic and configurable
* No real customer data is used
* The system is designed for **demonstration and adversarial evaluation**

---

## 🔐 Security & Ethics

This project does **not**:

* Process real UPI data
* Make enforcement decisions
* Replace human analysts

It is strictly an **educational and evaluative system**.

---

## 🏁 Conclusion

This project demonstrates how **graph-based analysis** can be used to identify mule-like and collusive behavior in digital payment systems while remaining:

* Explainable
* Testable
* Defensible under adversarial conditions
