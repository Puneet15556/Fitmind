"""
Convert FitMind dataset -> Qwen chat (messages) format for SFT.

Each example becomes a 3-role conversation:
  system    -> FitMind identity + output rules
  user      -> profile/budget + today's meals (memory) + the new input
  assistant -> JSON answer (items, calories, totals, reply)

The SFTTrainer (Week 2 training) applies Qwen's chat template to these
"messages" automatically. We keep the assistant target as compact JSON so the
phone app can parse it directly, while still containing the natural reply.

Input:  train.jsonl / val.jsonl / test.jsonl
Output: train_chat.jsonl / val_chat.jsonl / test_chat.jsonl

Run: python scripts/to_chat_format.py
"""

import json
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

SYSTEM_PROMPT = (
    "You are FitMind, an offline calorie tracker for Indian gym users. "
    "The user logs food in English, Hindi, or Hinglish. "
    "Extract the food items, estimate calories as a [min, max] range, sum the "
    "macros, add this meal to the running daily total from the context, and "
    "compute the remaining budget. Reply briefly in the SAME language as the "
    "user. Always answer with a single JSON object."
)


def format_context(ctx):
    """Turn the memory context into a readable block for the user message."""
    budget = ctx.get("budget", 2000)
    total = ctx.get("total_cal_so_far", 0)
    meals = ctx.get("today_meals", []) or []

    lines = [f"Daily budget: {budget} cal"]
    if meals:
        eaten = "; ".join(
            f"{m.get('meal','?')} ({m.get('cal',['?','?'])[0]}-{m.get('cal',['?','?'])[1]} cal)"
            if isinstance(m.get("cal"), list) else f"{m.get('meal','?')}"
            for m in meals
        )
        lines.append(f"Eaten today: {eaten}")
        lines.append(f"Total so far: {total} cal")
    else:
        lines.append("Eaten today: nothing yet")
        lines.append("Total so far: 0 cal")
    return "\n".join(lines)


def build_assistant_json(output):
    """Compact JSON the app can parse, preserving the natural reply."""
    obj = {
        "items": output.get("items", []),
        "calories": output.get("calories", [0, 0]),
        "protein_g": output.get("protein_g", 0),
        "carbs_g": output.get("carbs_g", 0),
        "fat_g": output.get("fat_g", 0),
        "fiber_g": output.get("fiber_g", 0),
        "today_total": output.get("today_total", [0, 0]),
        "budget_left": output.get("budget_left", [0, 0]),
        "reply": output.get("reply", ""),
    }
    # ensure_ascii=False keeps Hindi readable
    return json.dumps(obj, ensure_ascii=False)


def to_messages(ex):
    ctx_block = format_context(ex.get("context", {}))
    user_msg = f"{ctx_block}\n\nUser ({ex['lang']}): {ex['input']}"
    assistant_msg = build_assistant_json(ex["output"])
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
    }


def convert_file(name):
    src = DATA_DIR / f"{name}.jsonl"
    dst = DATA_DIR / f"{name}_chat.jsonl"
    rows = [json.loads(l) for l in src.open(encoding="utf-8")]
    with dst.open("w", encoding="utf-8") as f:
        for ex in rows:
            f.write(json.dumps(to_messages(ex), ensure_ascii=False) + "\n")
    return len(rows), dst


if __name__ == "__main__":
    for split in ["train", "val", "test"]:
        n, dst = convert_file(split)
        print(f"{split:6s}: {n:>4} examples -> {dst.name}")

    # Preview one full conversation
    print("\n" + "=" * 60)
    print("SAMPLE CONVERSATION (train_chat.jsonl, first row)")
    print("=" * 60)
    first = json.loads((DATA_DIR / "train_chat.jsonl").open(encoding="utf-8").readline())
    for m in first["messages"]:
        print(f"\n[{m['role'].upper()}]")
        print(m["content"])
