"""
Test suite for the hybrid layer (hybrid.py).

Runs assertion-based checks on:
  - CSV exact lookup (calories/macros)
  - calorie correction (model wrong -> hybrid right)
  - running total + budget recompute
  - language detection (hindi / hinglish / english)
  - translate fallback triggers only on mismatch
  - fuzzy matching (plurals, word order)
  - graceful handling of unknown foods

No pytest needed — run directly:
  python scripts/test_hybrid.py
Exits 0 if all pass, 1 if any fail.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from hybrid import HybridProcessor, detect_language, NutritionDB

hp = HybridProcessor()
db = hp.db

# Simple test runner -------------------------------------------------
_passed, _failed = 0, 0

def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")

def approx(a, b, tol=1):
    return abs(a - b) <= tol


# ====================================================================
print("\n[1] CSV exact lookup")
# ====================================================================
roti = db.lookup("roti")
check("roti exists", roti is not None)
check("roti calories = 75", approx(roti["cal"], 75), f"got {roti['cal']}")
check("roti protein = 2.5", approx(roti["protein"], 2.5), f"got {roti['protein']}")

rajma = db.lookup("rajma")
check("rajma calories = 200", approx(rajma["cal"], 200), f"got {rajma['cal']}")
check("rajma protein = 11", approx(rajma["protein"], 11), f"got {rajma['protein']}")


# ====================================================================
print("\n[2] Calorie/protein correction (the 12g -> 18.5g case)")
# ====================================================================
model_out = {
    "items": [{"name": "roti", "qty": 3}, {"name": "rajma", "qty": 1}],
    "calories": [280, 360], "protein_g": 12, "carbs_g": 42, "fat_g": 8, "fiber_g": 0,
    "reply": "3 roti aur rajma khaya, protein 12g.",
}
fixed = hp.process(model_out, "abhi 3 roti aur rajma khaya",
                   {"total_cal_so_far": 0, "budget": 2000})
# 3*2.5 + 11 = 18.5g protein expected
check("protein corrected to 18.5", approx(fixed["protein_g"], 18.5, 0.1),
      f"got {fixed['protein_g']}")
# 3*75 + 200 = 425 base; range ±12% => ~[374, 476]
check("calorie midpoint ~425", approx(sum(fixed["calories"]) / 2, 425, 5),
      f"got {sum(fixed['calories'])/2}")
check("both items matched", fixed["_meta"]["matched_items"] == ["roti", "rajma"])


# ====================================================================
print("\n[3] Running total + budget recompute")
# ====================================================================
model_out2 = {
    "items": [{"name": "samosa", "qty": 2}],
    "calories": [380, 440], "protein_g": 8, "carbs_g": 44, "fat_g": 22, "fiber_g": 3,
    "reply": "2 samose = 400 cal.",
}
fixed2 = hp.process(model_out2, "shaam ko 2 samose khaye",
                    {"total_cal_so_far": 920, "budget": 2000})
# samosa 200 cal each, 2 => 400 base; today = 920 + range
check("today_total starts from context (920+)", fixed2["today_total"][0] > 920,
      f"got {fixed2['today_total']}")
# budget_left = budget - today_total, ascending order
check("budget_left ascending", fixed2["budget_left"][0] <= fixed2["budget_left"][1])
check("budget_left = 2000 - today",
      approx(fixed2["budget_left"][1], 2000 - fixed2["today_total"][0]))


# ====================================================================
print("\n[4] Language detection")
# ====================================================================
check("devanagari -> hindi", detect_language("मैंने 2 रोटी खाई") == "hindi")
check("romanized hindi -> hinglish", detect_language("abhi maine roti khaya") == "hinglish")
check("plain english -> english", detect_language("I had two rotis for lunch") == "english")
check("english with food noun -> english", detect_language("I ate paneer") == "english")


# ====================================================================
print("\n[5] Reply built in target language with exact numbers")
# ====================================================================
# Reply is now BUILT in the target language with exact numbers (no translate).
import re as _re
def _has_dev(s): return bool(_re.search(r"[ऀ-ॿ]", s))

# hinglish input -> reply built in hinglish, with the EXACT corrected numbers
r_hin = hp.process(
    {"items": [{"name": "samosa", "qty": 2}], "calories": [999, 999],  # wrong on purpose
     "protein_g": 1, "reply": "wrong english reply with bad numbers"},
    "shaam ko 2 samose khaye",
    {"total_cal_so_far": 0, "budget": 2000})
reply = r_hin["reply"]
check("reply rebuilt (not the model's)", "wrong english" not in reply, f"got: {reply}")
check("reply has exact calories (352)", "352" in reply, f"got: {reply}")
check("reply not devanagari for hinglish", not _has_dev(reply))

# hindi input -> reply in devanagari
r_hi = hp.process(
    {"items": [{"name": "roti", "qty": 2}], "calories": [0, 0],
     "protein_g": 0, "reply": "english"},
    "मैंने 2 रोटी खाई", {"total_cal_so_far": 0, "budget": 2000})
check("hindi input -> devanagari reply", _has_dev(r_hi["reply"]), f"got: {r_hi['reply']}")

# english input -> english reply
r_en = hp.process(
    {"items": [{"name": "roti", "qty": 2}], "calories": [0, 0],
     "protein_g": 0, "reply": "x"},
    "I had 2 rotis", {"total_cal_so_far": 0, "budget": 2000})
check("english reply has 'Today'", "Today" in r_en["reply"], f"got: {r_en['reply']}")


# ====================================================================
print("\n[6] Fuzzy matching (plurals / word order)")
# ====================================================================
check("plural 'rotis' -> roti", db.lookup("rotis") is not None)
check("'butter paratha' finds paratha butter",
      db.lookup("butter paratha") is not None)
check("'chicken biryani' matches", db.lookup("chicken biryani") is not None)


# ====================================================================
print("\n[7] Unknown food handled gracefully")
# ====================================================================
out_unknown = hp.process(
    {"items": [{"name": "zzz_not_a_food", "qty": 1}], "calories": [100, 120],
     "protein_g": 5, "carbs_g": 10, "fat_g": 2, "fiber_g": 1, "reply": "ok"},
    "I ate zzz", {"total_cal_so_far": 0, "budget": 2000})
check("unknown item listed as unmatched",
      "zzz_not_a_food" in out_unknown["_meta"]["unmatched_items"])
check("no crash on unknown food", out_unknown is not None)


# ====================================================================
print("\n" + "=" * 45)
print(f"RESULTS: {_passed} passed, {_failed} failed")
print("=" * 45)
sys.exit(0 if _failed == 0 else 1)
