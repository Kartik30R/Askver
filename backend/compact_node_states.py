"""Compact legacy outputs/node_states.txt (append-history) into a single
JSON file representing the current workflow state. Overwrites the original
file with a single JSON object {"node": <last_node>, "state": {...}}.
"""
import json
from pathlib import Path

p = Path(__file__).parent / "outputs" / "node_states.txt"
if not p.exists():
    print("No snapshot file to compact:", p)
    raise SystemExit(1)

raw = p.read_text(encoding="utf-8")
parts = [part.strip() for part in raw.split("---") if part.strip()]
if not parts:
    print("No JSON parts found in snapshot; leaving unchanged.")
    raise SystemExit(1)

last = parts[-1]
obj = json.loads(last)

# Overwrite with a single JSON object
p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
print("Compacted snapshot; wrote single-state JSON to:", p)
