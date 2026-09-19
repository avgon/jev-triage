# jev-triage

Fast, structured ticket routing powered by [Jev](https://typesafe.ai). No LLM latency, no hallucination, just decisions.

> Jev doesn't generate text. It makes structured decisions: **choice**, **score**, **noul** (probability).

## Why?

LLMs are slow and expensive for ticket routing. Jev returns structured decisions in ~50ms. No prompt engineering, no output parsing, no "sorry I can't help with that."

```
Traditional LLM triage:
  User message → LLM (2-5s, $0.01) → parse JSON → hope it's valid → route

jev-triage:
  User message → Jev (50ms, $0.001) → typed result → route
```

## Install

```bash
pip install jev-triage
```

## Quick Start

```python
from jev_triage import Triage

t = Triage()  # uses TYPESAFE_API_KEY env var

result = t.classify("Faturamda yanlış tutar var, 500 TL fazla çekilmiş")
print(result)
# TriageResult(
#   department='billing',
#   urgency=2,          # 0=low, 1=medium, 2=critical
#   sentiment='negative',
#   frustrated=True,
#   revenue_impact=True,
#   language='tr',
#   tags=['refund', 'overcharge']
# )
```

## Features

### Multi-department routing

```python
t = Triage(departments={
    "billing": "Payment, invoice, refund, subscription issues",
    "shipping": "Delivery, tracking, address problems",
    "technical": "Bugs, API errors, integration issues",
    "sales": "Pricing, plans, enterprise inquiries",
    "hr": "Internal employee requests",
})

result = t.classify("The API returns 500 on POST /users endpoint")
assert result.department == "technical"
assert result.urgency >= 1
```

### Batch processing

```python
tickets = [
    "Can't login to my account",
    "Where is my order #12345?",
    "Your product changed my life, thank you!",
    "URGENT: production database is down",
]
results = t.classify_batch(tickets)

for ticket, result in zip(tickets, results):
    print(f"[{result.department}] P{result.urgency} | {ticket[:50]}")
```

### Custom scoring dimensions

```python
t = Triage(
    departments={"support": "General", "escalation": "Needs manager"},
    extra_signals={
        "is_legal_threat": {
            "type": "noul",
            "instructions": "Does the message contain a legal threat or mention lawyers/court?"
        },
        "is_churn_risk": {
            "type": "noul",
            "instructions": "Is the customer likely to cancel or leave?"
        },
    }
)

result = t.classify("I'm canceling my subscription and contacting my lawyer")
print(result.extra["is_legal_threat"])  # 0.92
print(result.extra["is_churn_risk"])    # 0.88
```

### Webhook / FastAPI integration

```python
from fastapi import FastAPI
from jev_triage import Triage

app = FastAPI()
triage = Triage()

@app.post("/triage")
async def triage_ticket(body: dict):
    result = triage.classify(body["message"])
    return {
        "route_to": result.department,
        "priority": result.urgency,
        "flags": {
            "frustrated": result.frustrated,
            "revenue_impact": result.revenue_impact,
        }
    }
```

### Pipeline mode (chain multiple classifiers)

```python
from jev_triage import Triage, Pipeline, EscalationRule

pipeline = Pipeline(
    triage=Triage(),
    rules=[
        EscalationRule(urgency=2, frustrated=True, route="escalation_queue"),
        EscalationRule(revenue_impact=True, route="retention_team"),
    ],
    default_route="general_queue",
)

result = pipeline.process("3 gündür ödeme yapamıyorum, müşterilerimi kaybediyorum!")
print(result.final_route)  # "escalation_queue"
print(result.applied_rule)  # "urgency=2 + frustrated"
```

### Language support

Jev handles any language natively. No translation needed.

```python
# Turkish
t.classify("Kargo 3 gündür gelmedi, rezalet!")

# English
t.classify("My payment failed and I need a refund ASAP")

# Japanese
t.classify("APIが500エラーを返しています。至急対応お願いします。")

# German
t.classify("Meine Rechnung stimmt nicht, bitte korrigieren")
```

## API Options

| Provider | Env Var | Endpoint |
|---|---|---|
| TypeSafe (direct) | `TYPESAFE_API_KEY` | `api.typesafe.ai` |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter.ai` |
| Custom | pass `base_url=` | Your proxy |

## Benchmarks

| Method | Latency | Cost/ticket | Accuracy |
|---|---|---|---|
| GPT-4 + JSON parse | 2-5s | ~$0.01 | 85% |
| Claude + tool_use | 1-3s | ~$0.008 | 87% |
| Fine-tuned BERT | 50ms | ~$0.0001 | 78% |
| **jev-triage** | **50ms** | **~$0.001** | **84%** |

*Accuracy measured on internal 500-ticket benchmark across 5 departments.*

## License

MIT
