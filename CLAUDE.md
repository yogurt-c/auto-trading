# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI-powered financial portfolio management tool built with Streamlit + Claude Agent SDK + Alpaca Paper Trading.

## Running

```bash
# Activate the virtual environment first
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env

# Run the Streamlit app
streamlit run app.py  # http://localhost:8501
```

## Environment

- Python 3.11 (managed via `venv/`)
- External dependencies in `requirements.txt`
- IDE: PyCharm (`.idea/` configuration present)
- Secrets in `.env` (gitignored)

## Architecture

```
app.py                    # Streamlit entry point
pages/
├── 1_Dashboard.py        # Portfolio overview, P&L, pie chart
├── 2_Holdings.py         # Holdings CRUD
├── 3_Analysis.py         # AI chat (orchestrator agent)
└── 4_Auto_Trading.py     # Auto trading config & logs
core/
├── database.py           # SQLite init (data/portfolio.db)
├── portfolio.py          # Data access layer
├── alpaca_client.py      # Alpaca API wrapper
├── tools.py              # Agent tool functions
└── agent.py              # Orchestrator + sub-agent logic
data/
└── portfolio.db          # Auto-created SQLite DB
```

## Agent Pattern

- **Orchestrator**: handles general Q&A, delegates to sub-agents via Task tool
- **Strategy Advisor sub-agent**: extracts structured strategy params, saves to DB
- **Trade Executor sub-agent**: checks strategy conditions, places Alpaca orders

## Key Notes

- Alpaca is configured for **Paper Trading** (safe for testing)
- DB auto-initializes on first run
- WebSearch is a built-in Anthropic API tool (`web_search_20250305`)
