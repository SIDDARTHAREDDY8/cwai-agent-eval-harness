"""CLI: run the eval across all scenarios (or one) and print JSON."""
import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.eval import evaluate, load_study, run_scenario, SCENARIOS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all",
                    help="all | " + " | ".join(SCENARIOS))
    args = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    study = load_study(root)

    if args.scenario == "all":
        with tempfile.TemporaryDirectory() as d:
            report = evaluate(study, audit_dir=d)
        print(json.dumps(report, indent=2))
    else:
        if args.scenario not in SCENARIOS:
            raise SystemExit(f"unknown scenario {args.scenario!r}")
        with tempfile.TemporaryDirectory() as d:
            report = run_scenario(
                study, args.scenario,
                audit_path=os.path.join(d, f"{args.scenario}.jsonl"))
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
