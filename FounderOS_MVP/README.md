# FounderOS

**AI Operating System for Smarter Business Decisions**

FounderOS is a Streamlit-based business intelligence and decision-support MVP for small and inexperienced business owners.

## Problem

Business owners often have sales, expenses, inventory, and customer records but struggle to turn those records into clear priorities.

## Solution

FounderOS follows:

**Business Data → Analysis → Problems → Priorities → Actions**

It combines deterministic Python/Pandas calculations with three specialized Gemini AI agents.

## Features

- Supabase email/password authentication
- CSV and Excel uploads
- Automatic file-type detection
- Optional business goal
- Missing-data tolerant analysis
- Finance dashboard
- Inventory dashboard
- Customers & Sales dashboard
- Business Health Score
- Three-agent AI analysis
- AI Business Advisor
- Plotly visualizations
- Human-friendly error messages
- Streamlit Community Cloud deployment

## AI Agents

### 1. Financial Intelligence Agent
Analyzes revenue, expenses, profit, trends, anomalies, warnings, and financial opportunities.

### 2. Operations Intelligence Agent
Analyzes inventory, products, customers, and sales patterns.

### 3. Strategy Agent
Receives the first two agents' findings and prioritizes the most important problems, opportunities, and recommended actions.

The application does not simply call one model three times: each agent has a distinct responsibility and the Strategy Agent is the final prioritization layer.

## Architecture

```text
CSV / Excel
    ↓
Data Processing
    ↓
Financial Intelligence Agent ──┐
                               ├──→ Strategy Agent → Priorities → Actions
Operations Intelligence Agent ─┘
    ↓
Dashboards + AI Advisor
```

## Input

Required:
- At least one usable CSV or Excel business record file.

Optional:
- Business Goal

You do not need to specify your business type.

Supported example files:
- Sales.xlsx
- Expenses.xlsx
- Inventory.xlsx
- Customers.xlsx

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- Google Gemini API
- Supabase Auth
- Supabase Database services
- Pydantic
- OpenPyXL

## Authentication

Supabase Auth handles account creation, login, session authentication, and logout. FounderOS does not implement its own password database.

## Secrets

For local development, create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-gemini-key"
GEMINI_MODEL = "gemini-3.6-flash"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-key"
```

Do **not** commit this file to GitHub.

A `.gitignore` should include:

```text
.streamlit/secrets.toml
.env
__pycache__/
*.pyc
```

## Installation

```bash
git clone <your-repository-url>
cd FounderOS
python -m venv .venv
```

Activate the environment and install:

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run app.py
```

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open Streamlit Community Cloud.
3. Select the repository.
4. Choose `app.py` as the main file.
5. Add the required secrets in the Streamlit Secrets settings.
6. Deploy.

## Project Structure

```text
FounderOS/
├── app.py
├── auth.py
├── sources.py
├── requirements.txt
├── README.md
├── pages/
│   ├── 1_🏠_Overview.py
│   ├── 2_💰_Finance.py
│   ├── 3_📦_Inventory.py
│   ├── 4_👥_Customers.py
│   └── 5_🤖_AI_Advisor.py
├── agents/
│   ├── financial_agent.py
│   ├── operations_agent.py
│   ├── strategy_agent.py
│   └── orchestrator.py
└── utils/
    ├── calculations.py
    └── helpers.py
```

## Privacy

Only upload business information you are authorized to share. FounderOS is designed to avoid unnecessary permanent storage of uploaded files and does not expose API keys in the interface.

This MVP should not be described as 100% secure. Production deployments should additionally review Supabase Row Level Security, retention policies, logging, rate limiting, and access controls.

## Limitations

- Automatic column recognition covers common naming variations but cannot understand every possible spreadsheet layout.
- Inventory value requires purchase-cost information.
- Customer analysis requires customer identifiers and purchase amounts.
- The Business Health Score is intentionally based only on measurable factors available in the uploaded records.
- AI interpretations can fail or be temporarily unavailable; deterministic metrics remain separate.
- For production use, add stronger schema validation, persistent per-user business workspaces, Row Level Security policies, and audit/logging controls.

## License

Add the license appropriate for your project before public release.
