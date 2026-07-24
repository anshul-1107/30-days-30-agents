"""
Day 2 / 30 - Supplier Email -> Structured Purchase Order

New concept vs Day 1: the model gets a second chance.

Day 1 was one call, take what you get. Here, if the output fails validation, the
error is fed back and the model tries again. That try -> check -> correct cycle is
the smallest possible agent loop. Weeks 3 and 4 are this same loop with more tools
in the middle.
"""

import json
import os
import sys
import time
from decimal import Decimal

from google import genai
from google.genai import types
from pydantic import ValidationError

from schema import PurchaseOrder

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODEL = "gemini-3.5-flash"
MAX_ATTEMPTS = 3

SYSTEM = """You extract purchase order data from messy supplier emails.

These emails are forwarded chains, WhatsApp-grade shorthand, and scanned-in text.
They are inconsistent on purpose. Your job is to be accurate, not complete.

Non-negotiable rules:
- If a field is not stated in the email, return null. Never infer a plausible value.
  A null PO number is a correct answer. An invented PO number is a costly error.
- Never calculate a total. Report only what the email literally states.
- Resolve relative dates against the received date given to you. If a date is too
  vague to resolve to a single day, return null and note it in ambiguities.
- Resolve quantity words to integers: "2 dozen" is 24, "500 nos" is 500.
- If the email is not an order at all, set is_purchase_order to false and return
  nothing else.
- Put every guess you made into ambiguities. An honest ambiguities list is worth
  more to us than a confidently filled form."""


def extract(email: dict) -> tuple[PurchaseOrder | None, list[str]]:
    """Call the model, validate, and retry with the validation error on failure."""
    if client is None:
        raise KeyError("Please set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
    email_text = (
        f"Email received on: {email['received']}\n"
        f"Subject: {email['subject']}\n\n"
        f"{email['body']}"
    )
    messages = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=email_text)]
        )
    ]
    attempts_log = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = None
        for api_attempt in range(5):
            try:
                resp = client.models.generate_content(
                    model=MODEL,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM,
                        temperature=0.0,
                        max_output_tokens=2000,
                        response_mime_type="application/json",
                        response_schema=PurchaseOrder,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                break
            except Exception as e:
                if any(err in str(e) for err in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
                    sleep_time = (api_attempt + 1) * 12
                    print(f"API temporary error ({e}), retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    raise e
        else:
            raise RuntimeError("API call failed after 5 rate limit retries")

        raw_json = resp.text.strip() if resp.text else ""
        if raw_json.startswith("```"):
            raw_json = raw_json.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            return PurchaseOrder.model_validate_json(raw_json), attempts_log
        except ValidationError as e:
            attempts_log.append(f"attempt {attempt}: {e.error_count()} error(s)")
            if attempt == MAX_ATTEMPTS:
                return None, attempts_log

            # Hand the model its own mistake and let it correct itself.
            messages.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=raw_json)]
                )
            )
            messages.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=(
                                f"Validation failed:\n{e}\n\n"
                                "Re-read the email and generate the JSON again with "
                                "corrected values. Do not guess to satisfy the "
                                "schema — use null where the email is silent."
                            )
                        )
                    ]
                )
            )

    return None, attempts_log


def cross_check(po: PurchaseOrder) -> dict:
    """Day 1's lesson, reapplied: the arithmetic is ours, not the model's."""
    if not po.is_purchase_order:
        return {}

    priced = [i for i in po.line_items if i.unit_price is not None]
    if len(priced) != len(po.line_items):
        return {"computed_total": None, "note": "some line items have no unit price"}

    computed = sum(Decimal(i.quantity) * i.unit_price for i in priced)
    out = {"computed_total": computed}

    if po.stated_total is not None:
        delta = computed - po.stated_total
        out["stated_total"] = po.stated_total
        out["delta"] = delta
        out["mismatch"] = abs(delta) > Decimal("0.01")
    return out


def render(email: dict, po: PurchaseOrder | None, log: list[str]) -> None:
    print(f"\n{'=' * 62}\n{email['id']}  |  {email['subject'][:45]}")

    if po is None:
        print(f"  FAILED after {MAX_ATTEMPTS} attempts: {log}")
        return
    if log:
        print(f"  (self-corrected: {log})")
    if not po.is_purchase_order:
        print("  Not a purchase order — skipped.")
        return

    print(f"  {po.supplier_name}   PO: {po.po_number or '— none stated —'}")
    print(f"  ordered {po.order_date or '?'}   delivery {po.expected_delivery or '?'}")
    for i in po.line_items:
        price = f"{po.currency} {i.unit_price:,}" if i.unit_price else "no price"
        print(f"    {i.sku or '(no sku)':<14} {i.quantity:>6} x {price:<16} {i.description[:28]}")

    check = cross_check(po)
    if check.get("computed_total") is not None:
        print(f"  computed: {po.currency} {check['computed_total']:,}")
        if check.get("mismatch"):
            print(f"  !! email states {po.currency} {check['stated_total']:,} "
                  f"— off by {check['delta']:,}. Hold for confirmation.")

    for a in po.ambiguities:
        print(f"  ? {a}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "emails.json"
    with open(path) as f:
        emails = json.load(f)

    for email in emails:
        po, log = extract(email)
        render(email, po, log)
    print()
