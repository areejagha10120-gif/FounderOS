import json
from sources import call_gemini_json
from utils.calculations import revenue, expense_total, profit, profit_margin, trend_pct
from utils.helpers import find_column

def run(datasets, goal=None):
    sales = datasets.get("sales")
    expenses = datasets.get("expenses")

    rev = revenue(sales)
    exp = expense_total(expenses)
    prof = profit(rev, exp)
    margin = profit_margin(rev, prof)

    facts = {
        "revenue": rev,
        "expenses": exp,
        "profit": prof,
        "profit_margin": margin,
        "revenue_trend_pct": trend_pct(sales) if sales is not None else None,
        "expense_trend_pct": trend_pct(expenses) if expenses is not None else None,
    }

    prompt = f"""
You are the Financial Intelligence Agent in FounderOS.
Analyze only the supplied calculated facts. Never invent numbers.
Goal: {goal or "None provided"}
Facts:
{json.dumps(facts, default=str)}

Return JSON with exactly:
{{
  "summary": "short plain-English summary",
  "problems": [{{"title": "...", "severity": "HIGH|MEDIUM|LOW", "evidence": "...", "action": "..."}}],
  "opportunities": [{{"title": "...", "evidence": "...", "action": "..."}}],
  "warnings": ["..."]
}}
If a metric is unavailable, say it is unavailable rather than estimating it.
"""
    try:
        ai = call_gemini_json(prompt)
    except Exception:
        ai = {"summary": "Financial calculations are available; AI interpretation is temporarily unavailable.",
              "problems": [], "opportunities": [], "warnings": []}
    return {"facts": facts, "ai": ai}
