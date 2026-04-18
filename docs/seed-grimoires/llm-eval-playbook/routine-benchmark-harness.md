# Routine — Benchmark harness for task agents

A minimum-viable structure for evaluating a task-completing agent
(e.g. "fix this bug", "summarise this transcript") reproducibly.

## When to apply

- You are changing a prompt, a model, a tool set, or any other input
  to an agent, and want to know if the change helps, hurts, or is
  noise.
- You're about to ship an agent-backed feature and need a baseline.

## Structure

```
benchmarks/
├── tasks/
│   ├── fix-bug-01.yaml
│   ├── fix-bug-02.yaml
│   └── ...
├── graders/
│   ├── compile_passes.py
│   └── test_passes.py
├── runner.py
└── results/
    └── 2026-04-18T12-00-agent-v3.jsonl
```

Each `tasks/*.yaml`:

```yaml
id: fix-bug-01
description: Repair broken import in module X.
repo_fixture: fixtures/repo-bug-01.tar.gz
success:
  - grader: compile_passes
  - grader: test_passes
    target: tests/test_module_x.py::test_imports
timeout_sec: 300
```

## Rules

### 1. Fix the fixture

The repo the agent starts from must be byte-identical every run. Ship
fixtures as tarballs, not live clones. A benchmark that passes on a
Tuesday and fails on a Thursday because upstream main moved is not
a benchmark.

### 2. Deterministic graders

Graders return `pass | fail | error`. They MUST NOT call the LLM or
any other nondeterministic judge for the core success signal. Use
compile, test, lint, or exact-output matches. LLM-as-judge is fine as
a secondary quality metric, not the pass/fail signal.

### 3. Run N times, report distribution

LLMs are stochastic. Run each task 5× per config. Report:

- Pass rate (success / total).
- Median latency.
- 95th-percentile latency.
- Mean cost per task (see cost-tracking routine).

A 10% pass-rate change on 5 runs per task is within noise. You need
≥20 runs to detect 10% deltas with confidence.

### 4. Separate training and eval tasks

Once you've seen an agent succeed on a task during prompt-tuning,
that task is "training" — it's no longer evidence. Hold back 30% of
tasks as eval-only, never looked at during iteration.

## Report format

Write results as JSONL — one line per run — so you can diff configs
later:

```json
{"task_id": "fix-bug-01", "config": "agent-v3", "run": 0, "status": "pass", "latency_ms": 45231, "cost_usd": 0.12}
```

## Anti-patterns

- **"It worked on my machine."** Use the fixtures, record the run,
  or it didn't happen.
- **Moving benchmarks.** Once a benchmark lives, it stays frozen.
  Add new ones, don't edit old ones.
- **Aggregate scores that hide regression.** Always report per-task
  pass rates alongside the mean.

## Done when

- Benchmark runs from a single command (`python runner.py --config=...`).
- Results are reproducible across machines given the same seed.
- Previous configs' results are archived and diffable.
