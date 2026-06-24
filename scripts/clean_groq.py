"""
Cleaning + validation pipeline for Groq-generated examples.

Takes raw groq_examples.jsonl (or a batch file) and:
  1. Fixes budget_left ordering ([high,low] -> [low,high])
  2. Fixes calories / today_total ordering if reversed
  3. Recomputes today_total = context.total + calories (trust the math)
  4. Recomputes budget_left = budget - today_total
  5. Re-tags language by detecting actual script/words (or drops if unsure)
  6. Drops examples missing required fields
  7. Dedupes by input text

Run:
  python scripts/clean_groq.py --in data/processed/groq_examples.jsonl
  python scripts/clean_groq.py --in <batch_file> --out <clean_file>

Output: <input>_clean.jsonl  (or --out path)
"""

import json
import re
import sys
import argparse
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

HINGLISH_WORDS = {
    "khaya", "khaaya", "maine", "mene", "abhi", "bacha", "aur", "kha",
    "liye", "rha", "raha", "subah", "shaam", "raat", "dopahar", "le",
    "ke", "saath", "tha", "diya", "hai", "ho", "gaya", "pi", "piya",
}


def has_devanagari(s):
    return bool(re.search(r"[ऀ-ॿ]", s or ""))


def looks_hinglish(s):
    words = set((s or "").lower().replace(",", " ").split())
    return len(words & HINGLISH_WORDS) >= 1


def detect_language(text):
    """Return english | hindi | hinglish based on actual content."""
    if has_devanagari(text):
        return "hindi"
    if looks_hinglish(text):
        return "hinglish"
    return "english"


def fix_pair(pair):
    """Ensure a [min, max] pair is correctly ordered."""
    if isinstance(pair, list) and len(pair) == 2:
        try:
            a, b = float(pair[0]), float(pair[1])
            return [int(min(a, b)), int(max(a, b))]
        except (TypeError, ValueError):
            return None
    return None


def clean_example(ex):
    """Return cleaned example or None if unsalvageable."""
    inp = ex.get("input", "").strip()
    out = ex.get("output", {})
    ctx = ex.get("context", {})

    if not inp or not isinstance(out, dict):
        return None

    # --- calories ---
    cal = fix_pair(out.get("calories"))
    if cal is None:
        return None
    out["calories"] = cal

    # --- context total + budget ---
    prev = ctx.get("total_cal_so_far", 0) or 0
    budget = ctx.get("budget", 2000) or 2000
    try:
        prev = float(prev)
        budget = float(budget)
    except (TypeError, ValueError):
        prev, budget = 0, 2000

    # --- recompute today_total = prev + calories (trust the math) ---
    today = [int(prev + cal[0]), int(prev + cal[1])]
    out["today_total"] = today

    # --- recompute budget_left = budget - today_total (correct order) ---
    out["budget_left"] = [int(budget - today[1]), int(budget - today[0])]

    # --- re-tag language from actual content ---
    ex["lang"] = detect_language(inp)

    # --- ensure macros exist (default 0) ---
    for k in ("protein_g", "carbs_g", "fat_g", "fiber_g"):
        if k not in out:
            out[k] = 0

    # --- items must exist ---
    if "items" not in out or not isinstance(out["items"], list):
        out["items"] = []

    ex["output"] = out
    return ex


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile",
                        default=str(DATA_DIR / "groq_examples.jsonl"))
    parser.add_argument("--out", dest="outfile", default=None)
    args = parser.parse_args()

    infile = Path(args.infile)
    outfile = Path(args.outfile) if args.outfile else \
        infile.with_name(infile.stem + "_clean.jsonl")

    raw = [json.loads(l) for l in infile.open(encoding="utf-8")]

    cleaned = []
    seen_inputs = set()
    dropped = 0
    deduped = 0

    for ex in raw:
        c = clean_example(ex)
        if c is None:
            dropped += 1
            continue
        key = c["input"].strip().lower()
        if key in seen_inputs:
            deduped += 1
            continue
        seen_inputs.add(key)
        cleaned.append(c)

    with outfile.open("w", encoding="utf-8") as f:
        for ex in cleaned:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    from collections import Counter
    langs = Counter(e["lang"] for e in cleaned)

    print(f"Input:    {len(raw)} examples")
    print(f"Dropped:  {dropped} (bad/missing fields)")
    print(f"Deduped:  {deduped} (duplicate inputs)")
    print(f"Clean:    {len(cleaned)} -> {outfile}")
    print(f"\nLanguage breakdown (after re-tagging):")
    for k, v in langs.most_common():
        print(f"  {k:10s}: {v}")


if __name__ == "__main__":
    main()
