"""
FitMind interactive CLI — chat with the REAL GGUF model + hybrid + memory.

Run:
  python scripts/fm_chat.py                      # uses models/fitmind-Q4_K_M.gguf
  python scripts/fm_chat.py --mock               # no model, mock mode
  python scripts/fm_chat.py --model path.gguf

Type meals in English/Hindi/Hinglish. Type 'reset' to clear today, 'quit' to exit.
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from fm_engine import FitMindEngine

DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "models" / "fitmind-Q4_K_M.gguf"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--budget", type=int, default=2000)
    args = ap.parse_args()

    import tempfile, os
    db = os.path.join(tempfile.gettempdir(), "fm_chat.db")

    print("Loading FitMind engine...", "(mock)" if args.mock else f"({args.model})")
    if args.mock:
        engine = FitMindEngine(mock=True, db_path=db, default_budget=args.budget)
    else:
        engine = FitMindEngine(model_path=args.model, db_path=db, default_budget=args.budget)
    engine.memory.set_budget(1, args.budget)
    print(f"Ready. Daily budget: {args.budget} cal.")
    print("Type a meal (any language), or 'reset' / 'quit'.\n")

    while True:
        try:
            msg = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.lower() in ("quit", "exit"):
            break
        if msg.lower() == "reset":
            engine.memory.reset_day(1)
            print("  (today reset)\n")
            continue

        result = engine.process(msg, user_id=1)
        if "error" in result:
            print("  [error]", result["error"], "\n")
            continue

        meta = result.get("_meta", {})
        print(f"\nfit > {result.get('reply','')}")
        print(f"      calories: {result['calories']}  protein: {result['protein_g']}g")
        print(f"      today: {result['today_total']}  budget left: {result['budget_left']}")
        if meta.get("unmatched_items"):
            print(f"      (not in DB, skipped: {meta['unmatched_items']})")
        if meta.get("translated"):
            print(f"      (reply translated to {meta['target_lang']})")
        print()

    print("\nbye! 💪")


if __name__ == "__main__":
    main()
