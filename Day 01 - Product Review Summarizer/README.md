# 📊 Product Review Summarizer: Verified eCommerce Intelligence

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.46-red.svg)](https://streamlit.io/)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Gemini-2.5%20Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered eCommerce review summarization agent built using **Google Gemini 2.5 Flash** and **Streamlit**. The project features a hybrid architecture combining LLM judgement with a Python verification layer to completely eliminate numerical hallucinations in generated merchant briefings.

---

## 💡 The Core Problem: "LLMs Cannot Count"

When asked to summarize customer reviews and report statistics (e.g., *"40% of customers complained about shipping"*), raw LLMs often produce numbers that "look plausible" but are mathematically incorrect or cite non-existent reviews. Making inventory or supplier decisions based on these numbers can cost eCommerce brands thousands of dollars.

### The Solution: Split of Responsibilities Pattern
This project resolves the hallucination issue by splitting the responsibilities:

| Job | Owner | Implementation |
| :--- | :--- | :--- |
| **Judgement** (Is this review about battery life?) | **LLM** (Gemini) | Semantic classification & tag mapping |
| **Arithmetic** (How many reviews, what percentage?) | **Python** (Code) | Deterministic count calculation and validation |

The system prompt forbids Gemini from generating any numbers, counts, or percentages. Instead, the model is strictly configured to return JSON with list references of raw review IDs (e.g., `["R002", "R008"]`). The Python code then:
1. Re-calculates percentages and counts deterministically.
2. Cross-references the cited review IDs against the source dataset to filter out hallucinations (flagged in the UI).

---

## ⚡ Features

- **Gemini API Integration**: Leverages `google-genai` and `gemini-2.5-flash` with disabled thinking budgets for optimal latency and response time.
- **Strict JSON Output Enforcement**: Uses Gemini's native `response_mime_type="application/json"` to ensure structural compliance.
- **Robust Python Verification**: Performs automatic validation on citations to detect and drop hallucinated IDs.
- **Dynamic Streamlit Web Interface**: 
  - File upload supporting custom reviews datasets.
  - Interactive rating breakdown and data previewer.
  - Color-coded cards for overall sentiment (Positive, Mixed, Negative) and priority severities (High, Medium, Low).
  - Side-by-side view of Product issues vs. Fulfilment issues (enabling distinct operational action items).
- **Flexible Schema Mapper**: Normalizes uploaded JSON data (mapping dynamic columns like `stars` or `body` to `rating` and `text`).

---

## 🛠️ Architecture Workflow

```
[Raw Reviews JSON] 
       │
       ▼
[Streamlit App (Form Mapping / Normalization)]
       │
       ├─────────────────────────────────────┐
       ▼                                     ▼
 [Build Text Prompt]                 [Verify Review IDs]
       │                                     │
       ▼                                     │
[Gemini 2.5 Flash API]                       │
 (JSON Mode / ID List Citation)              │
       │                                     │
       ▼                                     ▼
[Raw JSON Summary Output] ──────────► [Python Verification Layer]
                                             │
                                             ▼
                                  [Recomputed Stats / Clean Citations]
                                             │
                                             ▼
                                  [Interactive Dashboard]
```

---

## 🚀 Getting Started

### Prerequisites

Clone this repository and install dependencies:
```bash
pip install google-genai streamlit pandas
```

### Configuration

Export your Gemini API Key:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```
*(Alternatively, you can input the API Key directly inside the Streamlit sidebar config)*

### Running the Application

#### 🖥️ Streamlit Web Dashboard (Recommended)
```bash
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

#### 🐚 CLI Utility
To run the summarization directly in your terminal:
```bash
python agent.py reviews.json
```

---

## 📊 Sample Output Preview

```text
  SENTIMENT: NEGATIVE   (25 reviews, ratings {1: 5, 2: 5, 3: 4, 4: 5, 5: 6})

  PRODUCT ISSUES
    [high] Battery life shorter than advertised
      7 reviews (28%)  R002, R008, R011, R016, R020, R021, R025
    [high] Charging case durability (lid/latch/hinge)
      5 reviews (20%)  R003, R004, R013, R018, R025
    [medium] Earbud charging issues
      1 reviews (4%)  R007

  FULFILMENT ISSUES
    [medium] Shipping speed
      1 reviews (4%)  R006
    [high] Wrong item received
      1 reviews (4%)  R024

  ACTION: Address the battery life discrepancy and charging case durability. Improve quality control for packaging and shipping accuracy.
```

---

## 🔮 Future Scalability
For production deployments handling thousands of reviews:
1. **Day 8 (RAG)**: Introduce Vector Search to retrieve reviews matching specific target categories.
2. **Day 11 (Chunked Analysis)**: Process reviews in parallel map-reduce batches to stay within LLM context window constraints.
