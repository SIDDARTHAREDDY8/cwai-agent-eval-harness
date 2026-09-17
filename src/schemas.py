"""JSON schemas for each agent's structured output.

Deterministic check #1: schema conformance. If an agent cannot emit the
contract it was given, nothing downstream may trust it.
"""
SCHEMAS = {
    "planner": {
        "required": {"plan_id": str, "steps": list, "standards_needed": list},
    },
    "retriever": {
        "required": {"query": str, "hits": list},
        "hit_fields": {"std_id": str, "score": (int, float), "title": str},
    },
    "calculator": {
        "required": {"total_mw": (int, float), "tolerance_mw": (int, float)},
    },
    "checker": {
        "required": {"standard_id": str, "verdict": str, "detail": str},
        "verdicts": {"pass", "fail"},
    },
    "writer": {
        "required": {"summary": str, "citations": list, "total_mw": (int, float)},
    },
}


def validate(agent, payload):
    """Return a list of schema violations (empty = conformant)."""
    spec = SCHEMAS[agent]
    problems = []
    for field, types in spec["required"].items():
        if field not in payload:
            problems.append(f"missing field '{field}'")
        elif not isinstance(payload[field], types):
            problems.append(f"field '{field}' has wrong type "
                            f"{type(payload[field]).__name__}")
    if agent == "retriever" and isinstance(payload.get("hits"), list):
        for i, h in enumerate(payload["hits"]):
            for f, t in spec["hit_fields"].items():
                if f not in h:
                    problems.append(f"hits[{i}] missing '{f}'")
                elif not isinstance(h[f], t):
                    problems.append(f"hits[{i}].{f} wrong type")
    if agent == "checker" and payload.get("verdict") not in spec["verdicts"]:
        problems.append(f"verdict must be one of {sorted(spec['verdicts'])}")
    return problems
