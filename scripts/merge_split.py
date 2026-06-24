"""
Merge all dataset sources -> normalize -> dedupe -> shuffle -> split.

Takes all 6 example files and produces final training-ready splits:
  - train.jsonl  (90%)  -> model learns from this
  - val.jsonl    (5%)   -> checked during training
  - test.jsonl   (5%)   -> final exam, model never trains on this

Every example is normalized to a unified schema:
  {
    "lang":      english | hindi | hinglish,
    "source":    where it came from (for analysis),
    "context":   {today_meals, total_cal_so_far, budget},
    "input":     user's message,
    "output":    {items, calories, protein_g, ..., today_total, budget_left, reply}
  }

Run: python scripts/merge_split.py
"""

import json
import random
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

# Source file -> source tag
SOURCES = {
    "gold_examples.jsonl":        "manual",
    "generated_examples.jsonl":   "programmatic_single",
    "combo_examples.jsonl":       "programmatic_combo",
    "groq_examples_clean.jsonl":  "distill_b1",
    "groq_b2_clean.jsonl":        "distill_b2",
    "groq_b3_clean.jsonl":        "distill_b3",
}

VALID_LANGS = {"english", "hindi", "hinglish"}


def normalize(ex, source_tag):
    """Coerce any example into the unified schema; return None if unusable."""
    inp = (ex.get("input") or "").strip()
    out = ex.get("output")
    if not inp or not isinstance(out, dict):
        return None

    lang = ex.get("lang", "")
    if lang not in VALID_LANGS:
        return None

    # output must have a reply and calories
    if "reply" not in out or "calories" not in out:
        return None

    context = ex.get("context", {}) or {}

    return {
        "lang": lang,
        "source": ex.get("source", source_tag),
        "meal_type": ex.get("meal_type", ""),
        "context": {
            "today_meals": context.get("today_meals", []),
            "total_cal_so_far": context.get("total_cal_so_far", 0),
            "budget": context.get("budget", 2000),
        },
        "input": inp,
        "output": out,
    }


def main():
    all_examples = []
    per_source = {}

    for fname, tag in SOURCES.items():
        path = DATA_DIR / fname
        if not path.exists():
            print(f"  WARN: {fname} missing, skipping")
            continue
        count = 0
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue
            norm = normalize(ex, tag)
            if norm:
                all_examples.append(norm)
                count += 1
        per_source[tag] = count

    # Dedupe by (lang, input) — same sentence in same language = duplicate
    seen = set()
    deduped = []
    for ex in all_examples:
        key = (ex["lang"], ex["input"].lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ex)

    dropped_dupes = len(all_examples) - len(deduped)

    # Shuffle
    random.shuffle(deduped)

    # Split 90 / 5 / 5
    n = len(deduped)
    n_val = max(1, int(n * 0.05))
    n_test = max(1, int(n * 0.05))
    val = deduped[:n_val]
    test = deduped[n_val:n_val + n_test]
    train = deduped[n_val + n_test:]

    # Write splits
    for name, rows in [("train", train), ("val", val), ("test", test)]:
        outpath = DATA_DIR / f"{name}.jsonl"
        with outpath.open("w", encoding="utf-8") as f:
            for ex in rows:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Report
    from collections import Counter
    print("=" * 50)
    print("MERGE + SPLIT COMPLETE")
    print("=" * 50)
    print("\nPer-source (after normalize):")
    for tag, c in per_source.items():
        print(f"  {c:>4}  {tag}")
    print(f"\nTotal normalized:  {len(all_examples)}")
    print(f"Dropped dupes:     {dropped_dupes}")
    print(f"Final unique:      {len(deduped)}")
    print(f"\nSPLITS:")
    print(f"  train: {len(train)}  -> train.jsonl")
    print(f"  val:   {len(val)}  -> val.jsonl")
    print(f"  test:  {len(test)}  -> test.jsonl")

    lang_dist = Counter(e["lang"] for e in deduped)
    print(f"\nLanguage distribution:")
    for k, v in lang_dist.most_common():
        print(f"  {k:10s}: {v}  ({100*v/len(deduped):.0f}%)")

    src_dist = Counter(e["source"] for e in deduped)
    print(f"\nSource distribution:")
    for k, v in src_dist.most_common():
        print(f"  {k:22s}: {v}")


if __name__ == "__main__":
    main()
