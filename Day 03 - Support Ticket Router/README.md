# Day 3 / 30 — Support Ticket Router

Classification with calibrated confidence, multi-intent detection, and — the actual
point — a model that's allowed to abstain and hand a ticket to a human.

## Run it

Install dependencies:
```bash
pip install google-genai pydantic streamlit plotly pandas python-dotenv
```

Set up your Gemini API key:
```bash
export GEMINI_API_KEY="your-api-key"
```

To run the command-line CLI classifier:
```bash
python agent.py tickets.json
```

To launch the beautiful interactive simulation dashboard:
```bash
streamlit run app.py
```

## The lesson: a confident classifier is a liability

Any model will classify any ticket into one of your categories. Feed it "hi" and
it will pick something. That's the failure. In a live support queue, a classifier
that guesses on every ticket doesn't save your team work — it *adds* work, because
now every misroute is a customer bounced to the wrong department and a human
untangling it after the fact.

The behaviour you actually want is the model knowing the difference between "this
is unmistakably a shipping delay" and "this is too vague to route." That's
**calibrated confidence**, and it's harder to get than classification. Models
default to sounding sure. The prompt here fights that directly: it tells the model
that a low score on a vague ticket is the *correct* answer, and that abstaining is
valued, not a failure.

## The routing bands live in Python, not the prompt

Same principle as Days 1 and 2 — the model judges, code decides. The model never
chooses what happens to a ticket. It returns a category and an honest confidence,
and `route()` applies thresholds:

| Confidence | What happens |
|---|---|
| ≥ 0.75 | Auto-route to the category queue |
| 0.45 – 0.75 | Route suggested, a human confirms |
| < 0.45 | Model abstained — human triages from scratch |

Those numbers are business policy. When your ops lead says "we're auto-routing too
much garbage," you tune one constant in code — you don't re-engineer a prompt and
re-test the whole thing. Keeping policy out of the model is what makes the system
maintainable.

## Urgency overrides confidence

There's a second override that matters: `urgency >= 5` jumps straight to a human,
even at moderate confidence. A suspected account breach or a legal threat shouldn't
wait in a category queue because the model was only 0.6 sure which category it was.
Stakes beat tidiness.

Note the urgency rule in the prompt: it's judged on *content, not tone*. A calm
"there are orders on my account I didn't place" is a 5. An all-caps "WHERE IS MY
ORDER" is a 2. Getting the model to separate genuine stakes from loud punctuation
is most of the work.

## What each ticket is testing

| | Trap |
|---|---|
| T001 | Clean single-category shipping. Should be high confidence, low urgency |
| T003 | Two intents — billing dispute **and** a GST invoice request. Must not collapse to one |
| T004 | "hi" — no content. Must score low and land in human triage, not a guessed queue |
| T005 | Legal threat + refund. Urgency should spike; category is `service_complaint` |
| T007 | Praise **and** a real product question. Primary shouldn't be `positive_feedback` if the question needs action |
| T008 | Not a support ticket at all — it's a purchase order (Day 2's data). Should be `spam_or_unclear` |
| T009 | Calm wording, maximum stakes. Account security, urgency 5, straight to a human |
| T010 | Product is fine — the complaint is about the delivery agent. Category is conduct, not defect |

## Experiments

1. Delete the "confidence must be calibrated" paragraph from `SYSTEM`. Re-run T004
   ("hi") and watch it get auto-routed somewhere with a straight face.
2. Raise `AUTO_ROUTE_MIN` to 0.9. More tickets go to humans, fewer misroutes —
   the precision/recall trade-off, expressed as one number you control.
3. Rewrite T009 in ALL CAPS with panic. Confirm urgency stays driven by content,
   not shouting. Then rewrite it as a shrug and confirm it *still* rates 5.
4. Add a ticket in a mix of Hindi and English. See whether confidence drops
   honestly or the model bluffs.

## Where this goes

The confidence gate is the same primitive as Day 16's human-in-the-loop approval.
Both are the system deciding, "I shouldn't act alone here." Today it's for routing;
Day 16 it's a checkpoint before an irreversible write. Same idea, higher stakes.
