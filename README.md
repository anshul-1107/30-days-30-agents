# 🚀 30 Days of AI Agents

Welcome to my **30 Days of AI Agents** repository! Over the next 30 days, I am building and documenting 30 distinct AI agents, ranging from simple zero-shot analytics engines to complex, multi-agent frameworks, task coordinators, and RAG systems.

This repository tracks my daily progress, architecture designs, and implementation details for each agent.

---

## 📅 Daily Progress Tracker

| Day | Agent Name | Description | Tech Stack |
| :--- | :--- | :--- | :--- |
| **01** | [Product Review Summarizer](./Day%2001%20-%20Product%20Review%20Summarizer) | eCommerce review intelligence briefing with Python-verified citation checking. | `Gemini 2.5 Flash`, `Streamlit`, `Python` |
| **02** | [Messy Supplier Email](./Day%2002%20-%20Messy%20Supplier%20Email) | Raw supplier email parsing to structured PO schemas with an iterative self-correction loop. | `Gemini 3.5 Flash`, `Python`, `Pydantic` |
| **03** | [Support Ticket Router](./Day%2003%20-%20Support%20Ticket%20Router) | Support tickets queue triage with calibrated confidence, urgency overrides, and dynamic threshold visualization. | `Gemini 3.5 Flash`, `Streamlit`, `Plotly`, `Python` |

---

## 🛠️ General Setup & Requirements

Each daily agent resides in its own subdirectory and contains a dedicated `README.md` with specific running instructions.

### Prerequisites

Make sure you have Python 3.12+ installed. To install common packages used across multiple agents:
```bash
pip install google-genai streamlit pandas
```

### API Keys
Set your Gemini API Key in your environment:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```
