"""Deterministic checks over a pipeline run.

1. schema_conformance   - every agent output matches its contract
2. retrieval_quality    - top hit score >= MIN_SCORE and hits are ranked
3. citation_grounding   - writer citations exist in the standards corpus AND
                          were actually returned by the retriever
4. numeric_consistency  - writer total equals feeder sum within tolerance
5. recovery_logged      - any tool failure produced a retry/fallback audit trail
"""
from .pipeline import MIN_SCORE
from .schemas import validate


def check_schema(outputs):
    problems = []
    for agent, payload in outputs.items():
        for p in validate(agent, payload):
            problems.append(f"{agent}: {p}")
    return problems


def check_retrieval(outputs):
    problems = []
    hits = outputs["retriever"]["hits"]
    if not hits:
        return ["retriever returned no hits"]
    scores = [h.get("score", 0) for h in hits]
    if max(scores) < MIN_SCORE:
        problems.append(f"best retrieval score {max(scores)} < {MIN_SCORE}")
    if scores != sorted(scores, reverse=True):
        problems.append("hits are not ranked by score")
    return problems


def check_citations(outputs, corpus_ids):
    problems = []
    retrieved = {h["std_id"] for h in outputs["retriever"]["hits"]}
    for c in outputs["writer"]["citations"]:
        if c not in corpus_ids:
            problems.append(f"citation {c} not in standards corpus (invented)")
        elif c not in retrieved:
            problems.append(f"citation {c} never retrieved (ungrounded)")
    return problems


def check_numeric(outputs, study):
    problems = []
    calc = outputs["calculator"]
    writer_total = outputs["writer"].get("total_mw")
    feeder_sum = round(sum(f["load_mw"] for f in study["client_study"]["feeders"]), 1)
    tol = calc.get("tolerance_mw", 0.5) if isinstance(
        calc.get("tolerance_mw"), (int, float)) else 0.5
    for name, val in (("calculator", calc.get("total_mw")),
                      ("writer", writer_total)):
        if not isinstance(val, (int, float)):
            problems.append(f"{name} total is not numeric: {val!r}")
        elif abs(val - feeder_sum) > tol:
            problems.append(f"{name} total {val} != feeder sum {feeder_sum} "
                            f"(tol {tol})")
    return problems


def check_recovery(outputs, recovery, audit_records):
    problems = []
    failed_steps = [r for r in audit_records
                    if r["outcome"].get("ok") is False]
    if failed_steps and not recovery:
        problems.append("tool failure occurred but no recovery was logged")
    return problems


def run_all(outputs, study, recovery, audit_records):
    corpus_ids = {s["id"] for s in study["standards"]}
    results = {
        "schema_conformance": check_schema(outputs),
        "retrieval_quality": check_retrieval(outputs),
        "citation_grounding": check_citations(outputs, corpus_ids),
        "numeric_consistency": check_numeric(outputs, study),
        "recovery_logged": check_recovery(outputs, recovery, audit_records),
    }
    failed = {k: v for k, v in results.items() if v}
    return {"checks": results, "failed_checks": sorted(failed),
            "passed": not failed}
