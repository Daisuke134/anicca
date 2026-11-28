"""Independent smoke receipt checks; no production admission or global score."""
import json
import statistics
from pathlib import Path

def audit(receipt):
    cases = receipt["cases"]
    expected = {cid: answer for cid, _, answer in cases}
    if len(expected) != len(cases):
        raise ValueError("duplicate case")
    result = {}
    for arm in ("magnitude", "magnitude_warm", "llama_cpp"):
        rows = receipt["results"][arm]
        if len(rows) != len(expected) or {r["case"] for r in rows} != set(expected):
            raise ValueError("unmatched cases")
        correct = valid = 0
        times = []
        for row in rows:
            text = row.get("text")
            v = isinstance(text, str) and bool(text.strip()) and "error" not in row
            c = False
            if v:
                valid += 1
                times.append(row["seconds"])
                if row["case"] == "json":
                    try:
                        parsed = json.loads(text)
                        c = isinstance(parsed, dict) and set(parsed) == {"send"} and parsed["send"] is False
                    except ValueError:
                        pass
                else:
                    c = text.strip() == expected[row["case"]]
            if v != row["valid"] or c != row["correct"]:
                raise ValueError("receipt flags disagree")
            correct += c
        result[arm] = {"attempted":len(rows),"valid":valid,"correct":correct,"median_valid_seconds":statistics.median(times) if times else None}
    return {"summary":result,"promotion_eligible":False,"scope":"authored_smoke_only"}
if __name__ == "__main__":
    import sys
    print(json.dumps(audit(json.loads(Path(sys.argv[1]).read_text())),indent=2))
