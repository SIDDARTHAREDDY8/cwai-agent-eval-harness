"""Deterministic verification of the eval harness.

Run with: python -m tests.run  (from the repo root)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.eval import SCENARIOS, evaluate, load_study  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAILED = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILED.append(name)
        if detail:
            print("   --", detail)


def main():
    study = load_study(ROOT)
    report = evaluate(study)
    by = {s["scenario"]: s for s in report["scenarios"]}

    check("clean scenario passes all checks",
          by["clean"]["verdict"] == "PASS",
          str(by["clean"]["failed_checks"]))
    check("tool_timeout scenario is recovered (not silently dropped)",
          by["tool_timeout"]["verdict"] == "RECOVERED",
          str(by["tool_timeout"]))
    for s in ("bad_retrieval", "schema_violation", "invented_citation",
              "number_mismatch"):
        check(f"fault '{s}' is caught",
              by[s]["verdict"] == "CAUGHT",
              f"failed_checks={by[s]['failed_checks']}")
    check("eval gate is all-green", report["all_good"])
    check("bad_retrieval caught by retrieval_quality",
          "retrieval_quality" in by["bad_retrieval"]["failed_checks"])
    check("schema_violation caught by schema_conformance",
          "schema_conformance" in by["schema_violation"]["failed_checks"])
    check("invented_citation caught by citation_grounding",
          "citation_grounding" in by["invented_citation"]["failed_checks"])
    check("number_mismatch caught by numeric_consistency",
          "numeric_consistency" in by["number_mismatch"]["failed_checks"])
    check("tool_timeout exercised a logged recovery",
          len(by["tool_timeout"]["recovery"]) > 0)

    print(f"\n{len(report['scenarios']) + 6 - len(FAILED)} passed, "
          f"{len(FAILED)} failed")
    if FAILED:
        sys.exit(1)


if __name__ == "__main__":
    main()
