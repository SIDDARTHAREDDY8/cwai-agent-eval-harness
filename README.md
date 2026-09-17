# agent-eval-harness

Deterministic evals + audit trail for multi-agent orchestration.

## Why this exists

Catalyst·Wayfare's own Lead AI Engineer posting says it plainly:
"Build evals and monitoring dashboards so we can tell whether each agent is
actually working"; "Evals are first-class artifacts, not an afterthought.
Agents we trust live behind audit trails." Their HN hiring post asks for
"deterministic checks, evals, monitoring" on multi-agent workflows where
engineering agents "ingest client data, retrieve applicable standards, and
run QA across long-form study lifecycles."
([jd-builder](https://catalystwayfare.ai/jd-builder),
[HN](https://news.ycombinator.com/item?id=49650855) — fetched 2026-09-17).

The failure this guards against: an orchestration that *looks* fine while a
retriever returns junk, a calculator emits the wrong type, a writer invents a
citation, or a tool timeout gets silently absorbed. This harness is a small,
working version of the gate such a team would run before promoting any
orchestration change.

## How it works

Mock pipeline (planner → retriever → calculator → checker → writer) over a
mock power-engineering study: feeder loads, a substation total, and three
mock standards. Five deterministic checks run on every scenario:

1. **schema_conformance** — each agent's output matches its JSON contract
2. **retrieval_quality** — top hit above score threshold, hits ranked
3. **citation_grounding** — writer citations exist in the corpus AND were
   actually returned by the retriever (no invented or ungrounded citations)
4. **numeric_consistency** — reported totals equal the feeder sum within
   tolerance
5. **recovery_logged** — a tool failure leaves a retry/fallback audit trail

Every step, check result, and recovery is appended to a JSONL audit trail
(`src/audit.py`) — nothing is overwritten.

Scenarios (fault injection): `clean`, `bad_retrieval`, `tool_timeout`,
`schema_violation`, `invented_citation`, `number_mismatch`. `tool_timeout`
is a resilience test: the pipeline must recover via retry, not merely avoid
failing checks.

## Run it

```bash
python3 -m tests.run                 # deterministic verification suite
python3 -m src.cli --scenario all     # full eval table as JSON
python3 -m src.cli --scenario invented_citation
```

Verified 2026-09-17 (Python 3, stdlib only, no network, no API keys):

| scenario         | expected  | result    | failed checks        |
|------------------|-----------|-----------|----------------------|
| clean            | PASS      | PASS      | —                    |
| tool_timeout     | RECOVERED | RECOVERED | — (retry succeeded, logged) |
| bad_retrieval    | CAUGHT    | CAUGHT    | retrieval_quality    |
| schema_violation | CAUGHT    | CAUGHT    | schema_conformance   |
| invented_citation| CAUGHT    | CAUGHT    | citation_grounding   |
| number_mismatch  | CAUGHT    | CAUGHT    | numeric_consistency  |

`python3 -m tests.run` → 12 passed, 0 failed.

## Honest notes

- The study, standards, agents, and faults are all MOCK. No LLM is called;
  the point is the eval design, not the mock agents.
- In production the same checks wrap the real orchestration: swap
  `src/pipeline.py` for the real agents, keep `src/checks.py`,
  `src/audit.py`, and the scenario gate.
- This is a demo built as problem-first outreach — I have no access to
  Catalyst·Wayfare's internals.

Built by [Siddartha Reddy Chinthala](https://github.com/SIDDARTHAREDDY8).
