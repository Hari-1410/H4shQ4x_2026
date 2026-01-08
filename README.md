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

## 🔁 Real-World Workflow 

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
---

## API INSTALLATION
This project is *fully containerized* and can be executed on any machine with Docker support.  
No Python installation or manual dependency setup is required.

---

### ✅ Prerequisites

Ensure the following are installed on your system:

- *Docker*
- *Docker Compose*

> Tested on Windows, Linux, and macOS using Docker Desktop.

---

### 🚀 Step-by-Step Setup

#### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Hari-1410/H4shQ4x_2026.git
cd H4shQ4x_2026

Start the System

From the root of the repository, run:

docker compose up --build


This command will:

Build the Fraud Analysis API (FastAPI)

Build the Analyst Console (Streamlit)

Start both services in a shared Docker network



3.Access the Services

Once the containers are running, open your browser:

Fraud Analysis API

http://localhost:8000


Health check:

http://localhost:8000/health


Analyst Console (UI)

http://localhost:8501


The analyst console allows you to submit transaction batches, view risk scores, explanations, and inspect graph-based evidence.

🧪 Demo Input 

Paste the following JSON into the Analyst Console to test the system:

{
  "transactions": [
    {
      "sender": "U1",
      "receiver": "M1",
      "amount": 5200,
      "time": "2024-01-01T11:00:00"
    },
    {
      "sender": "U2",
      "receiver": "M2",
      "amount": 5100,
      "time": "2024-01-01T11:01:00"
    },
    {
      "sender": "M1",
      "receiver": "R1",
      "amount": 5000,
      "time": "2024-01-01T11:02:00"
    },
    {
      "sender": "M2",
      "receiver": "R1",
      "amount": 4950,
      "time": "2024-01-01T11:03:00"
    },
    {
      "sender": "R1",
      "receiver": "M1",
      "amount": 4900,
      "time": "2024-01-01T11:04:00"
    },
    {
      "sender": "R1",
      "receiver": "M2",
      "amount": 4850,
      "time": "2024-01-01T11:05:00"
    }
  ]
}


Click Analyze Risk to view the results.

Stopping the System

To stop the containers, press:

CTRL + C


Or run:

docker compose down

🧠 NOTE

No real UPI or banking data is used

End users never interact with this system directly

All fraud detection logic resides in the backend API

Designed for simulation, adversarial testing, and evaluation



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



## 📊 Risk Interpretation

* **LOW** → benign behavior
* **MEDIUM** → requires monitoring
* **HIGH** → likely mule or collusive behavior

Each risk decision is accompanied by **explicit reasons** derived from graph metrics.

---

## 🖥️ Analyst Console 

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

## ⚠️ System Scope & Design Notes
* The system analyzes **transaction relationships** provided by upstream analysis or monitoring processes
* Risk indicators are derived from **structural and behavioral patterns** in the data
* Detection logic is **configurable** and designed for evaluative and testing contexts
---

## 🔐 Security & Ethics
* No real customer or financial data is processed or stored
* The system does not perform automated enforcement actions
* Human oversight is assumed in all usage scenarios


It is strictly an **educational and evaluative system**.

---

## 🏁 Conclusion

This project demonstrates how **graph-based analysis** can be used to identify mule-like and collusive behavior in digital payment systems while remaining:

* Explainable
* Testable
* Deployable


**Video link is attached in google drive with file name as "Video Link"**
