"""Append-only JSONL audit trail.

"Agents we trust live behind audit trails." Every agent step, every check
result, and every recovery event is one JSON line: timestamp, agent,
payload digest, and outcome. Nothing is overwritten.
"""
import hashlib
import json
import time


class AuditTrail:
    def __init__(self, path=None):
        self.path = path
        self.records = []
        self._fh = open(path, "a") if path else None

    def log(self, agent, payload, outcome):
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "agent": agent, "payload_sha": digest, "outcome": outcome}
        self.records.append(rec)
        if self._fh:
            self._fh.write(json.dumps(rec) + "\n")
            self._fh.flush()

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None
