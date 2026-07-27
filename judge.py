import argparse
import json
from collections import Counter
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

JUDGE_SYSTEM = (
    "You are a strict quality grader for a customer-service chatbot at "
    "American Backyard, an outdoor furniture store. You will be given the "
    "EXPECTED BEHAVIOR for a test case and the actual CONVERSATION. Grade "
    "the bot's replies against the expected behavior only — ignore tone, "
    "emoji, and length. PASS means every requirement in the expected "
    "behavior is met. PARTIAL means it is mostly met but a meaningful "
    "requirement is missed or weakened. FAIL means a core requirement is "
    "violated, or the bot invents facts. Respond with ONLY a JSON object, "
    'no other text: {"grade": "PASS"|"PARTIAL"|"FAIL", "reason": "one sentence"}'
)


def judge_case(entry):
    convo = "\n\n".join(
        f"CUSTOMER: {t['user']}\n\nBOT: {t['bot']}" for t in entry["turns"]
    )
    user_msg = (
        f"EXPECTED BEHAVIOR:\n{entry['expected']}\n\n"
        f"CONVERSATION:\n{convo}"
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        temperature=0,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = resp.content[0].text
    verdict = json.loads(text[text.find("{"): text.rfind("}") + 1])
    return verdict["grade"], verdict["reason"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_file")
    args = parser.parse_args()

    path = Path(args.results_file)
    results = json.loads(path.read_text())

    agree = 0
    graded = 0
    for i, entry in enumerate(results, 1):
        grade, reason = judge_case(entry)
        entry["judge_grade"] = grade
        entry["judge_reason"] = reason
        human = entry.get("grade")
        marker = ""
        if human:
            graded += 1
            if human == grade:
                agree += 1
                marker = "agree"
            else:
                marker = f"DISAGREE (you: {human})"
        print(f"[{i}/{len(results)}] {entry['id']:28} judge: {grade:8} {marker}")

    out = path.with_name(path.stem + "-judged.json")
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out}")

    if graded:
        print(f"\nJudge agreement with your grades: {agree}/{graded}")

    print("\n=== Baseline metrics (your grades) ===")
    counts = Counter(r.get("grade") for r in results if r.get("grade"))
    total = sum(counts.values())
    for g in ("PASS", "PARTIAL", "FAIL"):
        if counts.get(g):
            print(f"{g}: {counts[g]}/{total}")
    print("\nBy category:")
    by_cat = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r.get("grade"))
    for cat, grades in sorted(by_cat.items()):
        p = sum(1 for g in grades if g == "PASS")
        print(f"  {cat:22} {p}/{len(grades)} pass")