"""
Day 1 / 30 - Product Review Summarizer

One LLM call. No tools, no loops, no framework.
The whole lesson is in verify(): never trust a number the model gives you.
"""

import json
import os
import sys
from collections import Counter

from google import genai
from google.genai import types

# Use GEMINI_API_KEY or GOOGLE_API_KEY from environment
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "AIzaSyBEqwydqfw7iL7Ld8XxDxZXIVP8RFWNQQk"
if not api_key:
    raise KeyError("Please set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------- prompt

SYSTEM = """You are a product analyst for an ecommerce brand. You read customer \
reviews and report what is actually in them.

Rules:
- Only report themes supported by at least 2 reviews.
- Separate PRODUCT issues (defects, performance, design) from FULFILMENT issues \
(shipping, packaging, wrong item, support). Merchants act on these differently.
- For every theme, list the exact review IDs that support it. Do not include an ID \
unless that review genuinely mentions the theme.
- Never state a count, percentage, or proportion yourself. Return IDs only.
- Quote at most 8 words from any single review.

Return ONLY valid JSON matching this schema, no markdown fences, no preamble:
{
  "overall_sentiment": "positive" | "mixed" | "negative",
  "product_issues":   [{"theme": str, "severity": "high"|"medium"|"low", "review_ids": [str]}],
  "fulfilment_issues":[{"theme": str, "severity": "high"|"medium"|"low", "review_ids": [str]}],
  "strengths":        [{"theme": str, "review_ids": [str]}],
  "recommended_action": str
}"""


def build_prompt(data: dict) -> str:
    lines = [f"Product: {data['product']}", "", "Reviews:"]
    for r in data["reviews"]:
        lines.append(f"[{r['id']}] ({r['rating']}/5) {r['text']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- call

def summarize(data: dict) -> dict:
    resp = client.models.generate_content(
        model=MODEL,
        contents=build_prompt(data),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.0,
            max_output_tokens=2000,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw = resp.text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("Model did not return valid JSON:\n", raw, file=sys.stderr)
        raise


# ---------------------------------------------------------------- verify

def verify(result: dict, data: dict) -> dict:
    """Recompute every number in Python. Flag any ID the model invented."""
    valid_ids = {r["id"] for r in data["reviews"]}
    total = len(valid_ids)
    hallucinated = []

    for section in ("product_issues", "fulfilment_issues", "strengths"):
        for theme in result.get(section, []):
            ids = theme.get("review_ids", [])
            bad = [i for i in ids if i not in valid_ids]
            if bad:
                hallucinated.append((theme["theme"], bad))
            clean = sorted(set(ids) - set(bad))
            theme["review_ids"] = clean
            theme["count"] = len(clean)          # computed here, not by the model
            theme["pct"] = round(100 * len(clean) / total)

    result["_meta"] = {
        "total_reviews": total,
        "hallucinated_ids": hallucinated,
        "rating_distribution": dict(
            sorted(Counter(r["rating"] for r in data["reviews"]).items())
        ),
    }
    return result


# ---------------------------------------------------------------- output

def render(result: dict) -> None:
    m = result["_meta"]
    print(f"\n  SENTIMENT: {result['overall_sentiment'].upper()}   "
          f"({m['total_reviews']} reviews, ratings {m['rating_distribution']})\n")

    for label, key in [("PRODUCT ISSUES", "product_issues"),
                       ("FULFILMENT ISSUES", "fulfilment_issues"),
                       ("STRENGTHS", "strengths")]:
        themes = sorted(result.get(key, []), key=lambda t: -t["count"])
        if not themes:
            continue
        print(f"  {label}")
        for t in themes:
            sev = f"[{t['severity']}] " if "severity" in t else ""
            print(f"    {sev}{t['theme']}")
            print(f"      {t['count']} reviews ({t['pct']}%)  {', '.join(t['review_ids'])}")
        print()

    print(f"  ACTION: {result['recommended_action']}\n")

    if m["hallucinated_ids"]:
        print("  !! Model cited review IDs that do not exist:")
        for theme, bad in m["hallucinated_ids"]:
            print(f"     {theme}: {bad}")
        print()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "reviews.json"
    with open(path) as f:
        data = json.load(f)

    render(verify(summarize(data), data))
