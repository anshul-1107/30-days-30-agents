# Day 2 / 30 — Messy Supplier Email → Validated Purchase Order

Still one model per email, but now with a schema contract and a retry loop.

## Run it

Install dependencies:
```bash
pip install google-genai pydantic streamlit pandas
```

Set up your Gemini API key:
```bash
export GEMINI_API_KEY=AIzaSy...
```

Run the command-line agent:
```bash
python agent.py emails.json
```

Or launch the visual Streamlit dashboard:
```bash
streamlit run app.py
```

## Lesson 1: valid JSON is not correct JSON

Forcing a structured output schema (`response_schema`) guarantees the *shape* of the output. Every
field will be present, every type will be right, and it will parse cleanly.

None of that means it's true.

A schema-forced model handed an email with no PO number will happily return
`"po_number": "PO-2026-001"`. The field is a string, the schema is satisfied, the
parse succeeds, and you have just written a fabricated PO number into your ERP.
Nothing in your pipeline errors. You find out in three weeks.

**The API can guarantee valid JSON. It cannot guarantee true JSON.** That gap is
where extraction pipelines quietly rot, and closing it is a prompt-and-validation
job, not an API-parameter job.

So: every optional field is genuinely `Optional`, the system prompt states that a
null is a *correct answer*, and there's an `ambiguities` list that gives the model
somewhere to put its uncertainty other than into a field.

## Lesson 2: the retry loop

Day 1 was single-shot — one call, take what you get.

Here, when Pydantic rejects the output, the `ValidationError` goes back to the
model as a `tool_result` with `is_error: true`, and it tries again. Up to three
attempts, then the email is flagged for a human.

That cycle:

```
act → validate → feed the failure back → act again
```

is the entire idea behind agents. Day 15's LangGraph state machine and Day 17's
reflection agent are this loop with more steps in the middle. Everything else is
plumbing. Watch it fire on `E002` and `E005`.

## Lesson 3: computation stays in Python (again)

Same rule as Day 1, new application. The model reports the total the email
*claims*. Python multiplies out the line items and compares.

`E005` states ₹11,04,000. The line items sum to ₹11,40,000 — a digit
transposition, and one of the most common errors in supplier email. A model asked
to "extract the total" returns the wrong number confidently. A model forbidden
from calculating, plus code that does, catches it.

## What each sample email is testing

| | Trap |
|---|---|
| E001 | Indian numbering (`7,71,000`), `Rs.` vs `Rs`, relative date ("next Friday") |
| E002 | Almost nothing is stated — should return mostly nulls, not a filled form. `"2 dozen"` → 24 |
| E003 | Ambiguous date format: is `03/12/2026` March 12 or December 3? Should land in `ambiguities` |
| E004 | Not an order at all. Must be rejected, not force-fitted |
| E005 | Stated total contradicts the line items. Vague delivery ("end of month") |

## Experiments

1. Remove the "return null, never infer" rules from `SYSTEM`. Run E002. Count how
   many fields it invents.
2. Drop `MAX_ATTEMPTS` to 1 and see which emails fail that would otherwise recover.
3. Add `expected_delivery` before `order_date` to an email and watch the
   `model_validator` catch it and the model fix itself.
4. Note that money is `Decimal`, not `float`. `0.1 + 0.2 != 0.3` — never hold
   currency in a float, in an agent or anywhere else.

## Where this goes

This is the extraction half of a real accounts-payable workflow. Day 11 (pandas
analyst) and Day 30 (remittance rate-gap checker) both start with exactly this
step: unstructured document in, validated record out, discrepancies flagged.
