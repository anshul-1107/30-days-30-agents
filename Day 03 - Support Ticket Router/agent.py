"""
Day 3 / 30 - Support Ticket Router

New concept: the model is allowed to say "I don't know."

A classifier that guesses on every ticket looks impressive in a demo and quietly
misroutes 15% of a real queue. The valuable behaviour is the opposite of
confidence — knowing when to abstain and hand a ticket to a human. That decision
is the whole point of today.

Design, carried from Days 1-2:
  - the model classifies and rates its own confidence (judgement)
  - PYTHON decides what happens at each confidence level (control)
  - the routing thresholds live in code where they can be tuned, not in the prompt
"""

import json
import os
import re
import sys
import time
from enum import Enum

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODEL = "gemini-3.5-flash"

# --- routing thresholds: the business logic lives HERE, not in the prompt ------
AUTO_ROUTE_MIN   = 0.75   # at/above this, route automatically
REVIEW_BAND_MIN  = 0.45   # between this and AUTO_ROUTE_MIN, a human confirms the route
# below REVIEW_BAND_MIN, a human triages from scratch


class Category(str, Enum):
    shipping        = "shipping_delay"
    defect          = "product_defect"
    billing         = "billing_dispute"
    presales        = "presales_question"
    account_security= "account_security"
    complaint       = "service_complaint"
    praise          = "positive_feedback"
    spam_or_unclear = "spam_or_unclear"


class Classification(BaseModel):
    primary: Category = Field(description="The single best-fit category.")
    confidence: float = Field(
        ge=0, le=1,
        description="Your calibrated confidence in `primary`. Be honest. A vague or "
        "one-word ticket should score LOW even if you can guess. Reserve >0.9 for "
        "tickets where the category is unmistakable.",
    )
    secondary: list[Category] = Field(
        default_factory=list,
        description="Other categories genuinely present. A ticket asking for a refund "
        "AND a GST invoice has two intents — list the second here.",
    )
    urgency: int = Field(
        ge=1, le=5,
        description="1 = no time pressure, 5 = acute harm/loss happening now "
        "(security breach, legal threat, safety). Judge from content, not tone alone.",
    )
    reasoning: str = Field(description="One sentence. Why this category and confidence.")


SYSTEM = f"""You triage inbound customer support tickets for an ecommerce brand.

Categories:
- shipping_delay: order not arrived, tracking stuck, delivery timing
- product_defect: item broken, not working, faulty
- billing_dispute: double charge, wrong amount, refund status, invoice/GST requests
- presales_question: someone deciding whether to buy (compatibility, colours, specs)
- account_security: hacked account, unauthorized orders, credential issues
- service_complaint: unhappy with support, staff conduct, delivery agent behaviour
- positive_feedback: praise (may still contain a small question)
- spam_or_unclear: no actionable content, gibberish, or a message not meant for support

Rules:
- Confidence must be calibrated. A one-word or contentless ticket scores low even if
  you can guess a category. Do not be agreeable — be accurate.
- Many tickets carry more than one intent. Put the dominant one in `primary` and the
  rest in `secondary`. Do not collapse a two-part request into one category.
- urgency reflects real stakes, not volume of exclamation marks. A calm "my account
  has unauthorized orders" is a 5. An ALL-CAPS "where is my order" is a 2.
- You are not deciding what happens to the ticket. You classify and rate confidence
  honestly; downstream code handles routing. Abstaining (low confidence) is a valid
  and valued outcome."""


def classify(ticket: dict) -> Classification:
    if client is None:
        raise KeyError("Please set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

    resp = None
    for api_attempt in range(10):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=f"Channel: {ticket['channel']}\nTicket:\n{ticket['text']}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    temperature=0.0,
                    max_output_tokens=800,
                    response_mime_type="application/json",
                    response_schema=Classification,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            break
        except Exception as e:
            if any(err in str(e) for err in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
                # Try to extract exact retry delay from the Google API error message
                sleep_time = (api_attempt + 1) * 12
                match = re.search(r"Please retry in (\d+(?:\.\d+)?)s", str(e))
                if match:
                    sleep_time = float(match.group(1)) + 2.0
                print(f"API temporary error ({e}), retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                raise e
    else:
        raise RuntimeError("API call failed after 10 rate limit retries")

    raw = resp.text.strip() if resp and resp.text else ""
    if raw.startswith("```"):
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    return Classification.model_validate_json(raw)


def route(c: Classification) -> dict:
    """Python owns the decision. This is the part the model must NOT do."""
    # urgency overrides confidence: a probable security/legal issue goes to a human
    # fast, even if the model is only moderately sure.
    if c.urgency >= 5:
        return {"action": "ESCALATE — urgent human", "queue": "priority",
                "reason": "high stakes regardless of category"}

    if c.confidence >= AUTO_ROUTE_MIN:
        return {"action": "auto-route", "queue": c.primary.value, "reason": "confident"}

    if c.confidence >= REVIEW_BAND_MIN:
        return {"action": "human confirms suggested route", "queue": c.primary.value,
                "reason": "moderate confidence"}

    return {"action": "human triage from scratch", "queue": "unrouted",
            "reason": "low confidence — model abstained"}


def render(ticket: dict, c: Classification, r: dict) -> None:
    tag = {"auto-route": "  ->", "human confirms suggested route": "  ?",
           "human triage from scratch": "  !!", "ESCALATE — urgent human": "  !!!"}
    lead = "!!!" if c.urgency >= 5 else ("!!" if r["queue"] == "unrouted" else "->")
    print(f"\n{ticket['id']} [{ticket['channel']}]  {ticket['text'][:52]}...")
    print(f"  {lead} {c.primary.value}  (conf {c.confidence:.2f}, urgency {c.urgency})")
    if c.secondary:
        print(f"     also: {', '.join(s.value for s in c.secondary)}")
    print(f"     ACTION: {r['action']}  ->  queue: {r['queue']}")
    print(f"     {c.reasoning}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tickets.json"
    with open(path) as f:
        tickets = json.load(f)

    auto = human = 0
    for t in tickets:
        c = classify(t)
        r = route(c)
        render(t, c, r)
        auto += r["action"] == "auto-route"
        human += r["action"] != "auto-route"

    print(f"\n{'-'*60}\n{len(tickets)} tickets: {auto} auto-routed, "
          f"{human} sent to a human. "
          f"({100*auto//len(tickets)}% deflection)\n")
