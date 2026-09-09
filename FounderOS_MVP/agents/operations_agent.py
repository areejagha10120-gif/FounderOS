import json
from sources import call_gemini_json
from utils.calculations import inventory_metrics, customer_metrics

def run(datasets, goal=None):
    inventory = datasets.get("inventory")
    sales = datasets.get("sales")
    customers = datasets.get("customers")

    inv = inventory_metrics(inventory)
    cust = customer_metrics(customers if customers is not None else sales)

    sales_rows = int(len(sales)) if sales is not None else 0
    facts = {
        "inventory": inv,
        "customers": cust,
        "sales_records": sales_rows,
        "available_data": list(datasets.keys()),
    }

    prompt = f"""
You are the Operations Intelligence Agent in FounderOS.
Use only the supplied facts. Never invent numerical facts.
Goal: {goal or "None provided"}
Facts:
{json.dumps(facts, default=str)}

Return JSON:
{{
  "summary": "short plain-English summary",
  "problems": [{{"title": "...", "severity": "HIGH|MEDIUM|LOW", "evidence": "...", "action": "..."}}],
  "opportunities": [{{"title": "...", "evidence": "...", "action": "..."}}],
  "warnings": ["..."]
}}
"""
    try:
        ai = call_gemini_json(prompt)
    except Exception:
        ai = {"summary": "Operational calculations are available; AI interpretation is temporarily unavailable.",
              "problems": [], "opportunities": [], "warnings": []}
    return {"facts": facts, "ai": ai}
