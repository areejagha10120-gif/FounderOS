import json
from sources import call_gemini_json

def run(financial, operations, goal=None):
    payload = {
        "financial": financial,
        "operations": operations,
        "goal": goal,
    }
    prompt = f"""
You are the Strategy Agent for FounderOS.
You are the final decision-making layer. Prioritize instead of listing everything.
Use only the evidence supplied below. Do not invent facts.
Goal: {goal or "None provided"}

Evidence:
{json.dumps(payload, default=str)}

Return JSON:
{{
  "health_summary": "short assessment",
  "priorities": [
    {{
      "rank": 1,
      "title": "...",
      "priority": "HIGH|MEDIUM|LOW",
      "why": "...",
      "recommended_action": "..."
    }}
  ],
  "opportunities": ["..."],
  "warnings": ["..."]
}}
Limit priorities to the most important 3-5 items.
"""
    try:
        return call_gemini_json(prompt)
    except Exception:
        return {
            "health_summary": "Your calculated metrics are available, but AI prioritization is temporarily unavailable.",
            "priorities": [],
            "opportunities": [],
            "warnings": [],
        }
