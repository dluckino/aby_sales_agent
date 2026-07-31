import argparse
import json
import uuid
from datetime import date
from pathlib import Path

import requests

API_URL = "http://localhost:8000/chat"

CANARY_STRINGS = [
    ("knowledge/store_operations.md", "big green egg"),
    ("knowledge/store_operations.md", "only a portion"),
    ("knowledge/store_operations.md", "trade professionals"),
    ("knowledge/care_guides.md", "high-density polyethylene"),
    ("knowledge/store_operations.md", "does not feature all"),
]

def preflight():
    for path, needle in CANARY_STRINGS:
        if needle not in Path(path).read_text():
            raise SystemExit(
                f"PREFLIGHT FAIL: '{needle}' missing from {path} - "
                "make the content edit and re-run ingest before evals."
            )



def run_case(case):
    session_id = f"eval-{uuid.uuid4()}"
    turns = []
    for user_msg in case["turns"]:
        resp = requests.post(
            API_URL,
            json={"session_id": session_id, "message": user_msg},
            timeout=120,
        )
        resp.raise_for_status()
        turns.append({"user": user_msg, "bot": resp.json()["reply"]})
    return {
        "id": case["id"],
        "category": case["category"],
        "expected": case["expected"],
        "turns": turns,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-email-cases", action="store_true",
                        help="include cases marked sends_email (fires real staff emails)")
    args = parser.parse_args()
    preflight()

    try:
        requests.get("http://localhost:8000/health", timeout=5)
    except requests.exceptions.ConnectionError:
        raise SystemExit("Server not running - start it first: uvicorn main:app --reload")

    cases = json.loads(Path("evals/cases.json").read_text())
    if not args.send_email_cases:
        cases = [c for c in cases if not c.get("sends_email")]

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']}")
        results.append(run_case(case))

    out = Path(f"evals/results-{date.today()}.json")
    out.write_text(json.dumps(results, indent=2))
    print(f"Wrote {len(results)} results to {out}")
