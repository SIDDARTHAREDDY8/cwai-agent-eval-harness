"""Scenario runner: run every fault mode, run the deterministic checks,
and report which failure modes the harness catches.

A scenario is 'caught' if >=1 check fails for a fault mode, and the clean
mode must pass every check. This is the eval gate a team would run before
promoting an orchestration change.
"""
import json
import os

from .audit import AuditTrail
from .checks import run_all
from .pipeline import run_pipeline

# Expected outcome per scenario: the fault modes must be CAUGHT by >=1 check;
# tool_timeout is a resilience test and must be RECOVERED (checks green AND a
# retry/fallback logged); clean must PASS outright.
EXPECTED = {"clean": "PASS", "tool_timeout": "RECOVERED",
            "bad_retrieval": "CAUGHT", "schema_violation": "CAUGHT",
            "invented_citation": "CAUGHT", "number_mismatch": "CAUGHT"}


def load_study(root):
    with open(os.path.join(root, "data", "study.json")) as fh:
        return json.load(fh)


def run_scenario(study, scenario, audit_path=None):
    audit = AuditTrail(audit_path)
    try:
        outputs, recovery = run_pipeline(study, scenario, audit)
        result = run_all(outputs, study, recovery, audit.records)
    finally:
        audit.close()
    result["scenario"] = scenario
    result["recovery"] = recovery
    return result


def evaluate(study, audit_dir=None):
    reports = []
    for s in SCENARIOS:
        path = os.path.join(audit_dir, f"{s}.jsonl") if audit_dir else None
        reports.append(run_scenario(study, s, path))
SCENARIOS = list(EXPECTED)


def _verdict(r):
    exp = EXPECTED[r["scenario"]]
    if exp == "PASS":
        return "PASS" if r["passed"] else "FAIL"
    if exp == "RECOVERED":
        if not r["passed"]:
            return "FAIL"
        return "RECOVERED" if r["recovery"] else "NO_RECOVERY"
    return "CAUGHT" if not r["passed"] else "MISSED"


def evaluate(study, audit_dir=None):
    reports = []
    for s in SCENARIOS:
        path = os.path.join(audit_dir, f"{s}.jsonl") if audit_dir else None
        reports.append(run_scenario(study, s, path))
    table = []
    for r in reports:
        table.append({"scenario": r["scenario"], "verdict": _verdict(r),
                      "expected": EXPECTED[r["scenario"]],
                      "failed_checks": r["failed_checks"],
                      "recovery": r["recovery"]})
    return {"scenarios": table,
            "all_good": all(t["verdict"] == t["expected"] for t in table)}
