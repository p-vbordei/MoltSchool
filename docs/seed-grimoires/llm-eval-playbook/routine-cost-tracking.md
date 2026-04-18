# Routine — Per-request cost tracking

You cannot optimise what you do not measure. Per-request cost
attribution is the first thing you wire up before anyone is allowed
to ship an LLM-backed feature.

## When to apply

- Pre-launch of any agent or LLM-backed feature.
- Quarterly review of unit economics.
- Investigating unexpected bill spikes.

## What to capture

For every LLM call, store:

| Field              | Why                                               |
|--------------------|---------------------------------------------------|
| `request_id`       | Correlate with downstream logs and user sessions. |
| `user_id` / `tenant_id` | Per-customer unit economics.                 |
| `feature`          | Which product surface drove the call.             |
| `model`            | Vendor + version string (e.g. `claude-3.7-opus`). |
| `prompt_tokens`    | Input-side price component.                       |
| `completion_tokens`| Output-side price component.                      |
| `cached_tokens`    | Prompt cache hits (discounted).                   |
| `latency_ms`       | Observed wall clock.                              |
| `cost_usd`         | Computed from tokens + model price table.         |
| `success`          | Boolean: did the caller use the response?         |

Store as structured logs or in a cheap analytics sink (ClickHouse,
BigQuery, Redshift, DuckDB for small teams).

## Price table

Model prices change. Keep a single `prices.yaml` file and compute
`cost_usd` from it at write time — do NOT recompute historical costs
with current prices, or you lose the ability to diff "we changed
something" from "the vendor changed something".

```yaml
# prices.yaml — effective 2026-04-18
claude-3.7-opus:
  input_per_1m:  15.00
  output_per_1m: 75.00
  cached_per_1m: 1.50
```

## Dashboards

Build (or just save queries for) three views:

1. **Cost per active user per day.** Divergence from the trend line
   = someone shipped an expensive prompt.
2. **Cost per feature.** Catches regressions scoped to a single
   surface.
3. **Cached-token ratio.** If this drops, someone broke the cache
   (usually by injecting a timestamp or user-id into the system
   prompt).

## Budgets + alerts

Per-feature daily budget with a hard cap enforced at the client:

```python
if daily_feature_spend[feature] > BUDGET[feature]:
    raise BudgetExceeded(feature)
```

Pair with a softer alert at 80% of budget — gives the team a day to
respond before the hard cap triggers.

## Unit economics

Keep a single number on a wall: **cost per core transaction**. For a
chat product it's "cost per useful assistant message". For a
summarisation product it's "cost per delivered summary". When the
number moves, everyone notices.

## Done when

- Every LLM call writes a cost record.
- A dashboard shows daily cost per feature.
- A budget alert is wired up and has fired in test.
- You can answer "what did customer X cost us last month" in under
  5 minutes.
