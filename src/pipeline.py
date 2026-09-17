"""Mock multi-agent pipeline with seeded fault injection.

Agents: planner -> retriever -> calculator -> checker -> writer.
Every step emits a structured record; the audit module persists them.
Fault modes (one per scenario):
  clean             - the pipeline behaves
  bad_retrieval     - retriever returns a low-score, irrelevant hit
  tool_timeout      - retriever tool times out once; pipeline must retry, then
                      fall back to the standards cache, and log the recovery
  schema_violation  - calculator returns total_mw as a string
  invented_citation - writer cites a standard id that does not exist
  number_mismatch   - writer reports a total that does not match the feeders
"""
import time

RETRY_BUDGET = 1
MIN_SCORE = 0.5


class ToolTimeout(Exception):
    pass


def planner_run(study, fault):
    return {"plan_id": "plan-001",
            "steps": ["planner", "retriever", "calculator", "checker", "writer"],
            "standards_needed": ["WFR-GRID-01", "WFR-GRID-02"]}


def retriever_run(study, fault, attempt=0):
    if fault == "tool_timeout" and attempt == 0:
        raise ToolTimeout("standards index unreachable")
    if fault == "bad_retrieval":
        return {"query": "feeder loading standards",
                "hits": [{"std_id": "WFR-GRID-03", "score": 0.21,
                          "title": "Protection re-verification trigger"}]}
    corpus = {s["id"]: s for s in study["standards"]}
    hits = [{"std_id": sid, "score": 0.94 if sid in ("WFR-GRID-01", "WFR-GRID-02") else 0.62,
             "title": corpus[sid]["title"]}
            for sid in corpus]
    return {"query": "feeder loading standards", "hits": hits}


def calculator_run(study, fault):
    total = round(sum(f["load_mw"] for f in study["client_study"]["feeders"]), 1)
    if fault == "schema_violation":
        return {"total_mw": f"{total} MW", "tolerance_mw": 0.5}
    return {"total_mw": total, "tolerance_mw": 0.5}


def checker_run(study, fault, calc, retrieved_ids):
    if fault == "bad_retrieval":
        return {"standard_id": "WFR-GRID-03", "verdict": "fail",
                "detail": "retrieved standard does not address feeder loading"}
    diff = abs(calc["total_mw"] - study["client_study"]["total_mw"]) \
        if isinstance(calc.get("total_mw"), (int, float)) else 999
    if diff <= calc.get("tolerance_mw", 0.5):
        return {"standard_id": "WFR-GRID-02", "verdict": "pass",
                "detail": f"substation total consistent within tolerance (diff={diff})"}
    return {"standard_id": "WFR-GRID-02", "verdict": "fail",
            "detail": f"total mismatch: diff={diff} MW"}


def writer_run(study, fault, calc, check, retrieved_ids):
    total = calc.get("total_mw")
    if fault == "number_mismatch":
        total = 140.0
    citations = ["WFR-GRID-01", "WFR-GRID-02"]
    if fault == "invented_citation":
        citations = ["WFR-GRID-01", "WFR-GRID-99"]
    if fault == "bad_retrieval":
        citations = [h for h in retrieved_ids]
    return {"summary": f"QA of {study['client_study']['substation']}: total "
                       f"{total} MW across "
                       f"{len(study['client_study']['feeders'])} feeders; "
                       f"checker verdict {check['verdict']}.",
            "citations": citations,
            "total_mw": total}


def run_pipeline(study, fault, audit):
    """Run the pipeline; return (outputs, recovery_events). All steps audited."""
    outputs = {}
    recovery = []

    out = planner_run(study, fault)
    outputs["planner"] = out
    audit.log("planner", out, {"ok": True})

    # retriever with retry budget + fallback, per deterministic error recovery
    attempts = 0
    while True:
        try:
            out = retriever_run(study, fault, attempt=attempts)
            outputs["retriever"] = out
            audit.log("retriever", out, {"ok": True, "attempt": attempts + 1})
            if attempts > 0:
                recovery.append(
                    f"retriever timed out on attempt 1; retry {attempts + 1} "
                    f"succeeded within budget {RETRY_BUDGET}")
            break
        except ToolTimeout as e:
            attempts += 1
            audit.log("retriever", {"error": str(e)},
                      {"ok": False, "attempt": attempts})
            if attempts > RETRY_BUDGET:
                out = {"query": "feeder loading standards (cache fallback)",
                       "hits": [{"std_id": "WFR-GRID-01", "score": 0.80,
                                 "title": "Feeder loading assessment freshness (cached)"}]}
                outputs["retriever"] = out
                recovery.append("retriever exhausted retries; used cache fallback")
                audit.log("retriever", out, {"ok": True, "fallback": True})
                break
    retrieved_ids = [h["std_id"] for h in outputs["retriever"]["hits"]]

    out = calculator_run(study, fault)
    outputs["calculator"] = out
    audit.log("calculator", out, {"ok": True})

    out = checker_run(study, fault, outputs["calculator"], retrieved_ids)
    outputs["checker"] = out
    audit.log("checker", out, {"ok": True})

    out = writer_run(study, fault, outputs["calculator"], outputs["checker"],
                     retrieved_ids)
    outputs["writer"] = out
    audit.log("writer", out, {"ok": True})

    time.sleep(0)  # keep pipeline synchronous & deterministic
    return outputs, recovery
