"""
FitMind hybrid post-processing layer.

The SLM is great at language + extracting items, but its numbers drift
(eval: 122 cal MAE, and it guessed 12g protein where 18g was right).

This layer fixes that by applying the "tell, don't guess" principle:

  1. CSV LOOKUP   -> replace the model's guessed calories/macros with EXACT
                    values from nutrition.csv (deterministic, always correct)
  2. RECOMPUTE    -> today_total and budget_left from the exact numbers + context
  3. LANGUAGE     -> detect input language; if the model's reply is in the wrong
                    language, flag it (and optionally translate via a model hook)

Usage:
  from hybrid import HybridProcessor
  hp = HybridProcessor("data/processed/nutrition.csv")
  fixed = hp.process(model_output_dict, user_input, context, translate_fn=None)

The translate_fn (optional) is any callable str->str that re-expresses the reply
in the target language — at runtime this is a second call to the SLM itself.
"""

import csv
import re
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "processed" / "nutrition.csv"

# Real portions vary; CSV gives the reference. We keep a modest range on
# calories but report macros as exact sums (what the user actually cares about).
CAL_RANGE_PCT = 0.12

HINGLISH_WORDS = {
    "khaya", "khaaya", "khaye", "khaayi", "khai", "maine", "mene", "abhi",
    "bacha", "bachа", "aur", "kha", "liye", "raha", "rha", "subah", "shaam",
    "raat", "dopahar", "le", "ke", "saath", "tha", "diya", "ho", "gaya",
    "pi", "piya", "bhai", "yaar", "total", "budget",
}


# ----------------------------------------------------------------------
# Language detection (app-side, deterministic — the "tell" for language)
# ----------------------------------------------------------------------
def detect_language(text):
    """Return 'hindi' | 'hinglish' | 'english' from the text itself."""
    if re.search(r"[ऀ-ॿ]", text or ""):
        return "hindi"
    words = set((text or "").lower().replace(",", " ").replace(".", " ").split())
    if len(words & HINGLISH_WORDS) >= 1:
        return "hinglish"
    return "english"


# ----------------------------------------------------------------------
# Nutrition database (the "tell" for calories)
# ----------------------------------------------------------------------
class NutritionDB:
    def __init__(self, csv_path=DEFAULT_CSV):
        self.by_name = {}
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.by_name[row["food_name"].lower()] = {
                    "cal": float(row["calories"]),
                    "protein": float(row["protein_g"]),
                    "carbs": float(row["carbs_g"]),
                    "fat": float(row["fat_g"]),
                    "fiber": float(row["fiber_g"]),
                    "serving": row["typical_serving"],
                }

    def _normalize(self, name):
        n = (name or "").lower().strip()
        n = re.sub(r"\s+", " ", n)
        # strip trailing plural 's' on the last word (rotis -> roti)
        n = re.sub(r"s\b", "", n)
        return n

    def lookup(self, name):
        """Exact, then fuzzy (word-overlap) match. Returns nutrition dict or None."""
        n = self._normalize(name)
        # exact
        if n in self.by_name:
            return self.by_name[n]
        # try without normalization too
        raw = (name or "").lower().strip()
        if raw in self.by_name:
            return self.by_name[raw]
        # fuzzy: best word-overlap match
        qwords = set(n.split())
        best, best_score = None, 0
        for key, val in self.by_name.items():
            kwords = set(key.split())
            overlap = len(qwords & kwords)
            if overlap > best_score:
                best, best_score = val, overlap
        return best if best_score > 0 else None


# ----------------------------------------------------------------------
# The hybrid processor
# ----------------------------------------------------------------------
class HybridProcessor:
    def __init__(self, csv_path=DEFAULT_CSV):
        self.db = NutritionDB(csv_path)

    def compute_exact(self, items):
        """Sum exact nutrition from CSV for the model's extracted items.
        Returns (calories_range, macros_dict, matched_list, unmatched_list)."""
        total = {"cal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
        matched, unmatched = [], []
        for it in items:
            name = it.get("name", "")
            qty = it.get("qty", 1) or 1
            try:
                qty = float(qty)
            except (TypeError, ValueError):
                qty = 1
            info = self.db.lookup(name)
            if info is None:
                unmatched.append(name)
                continue
            for k in total:
                total[k] += info[k] * qty
            matched.append(name)

        cal_min = int(round(total["cal"] * (1 - CAL_RANGE_PCT)))
        cal_max = int(round(total["cal"] * (1 + CAL_RANGE_PCT)))
        macros = {
            "protein_g": round(total["protein"], 1),
            "carbs_g": round(total["carbs"], 1),
            "fat_g": round(total["fat"], 1),
            "fiber_g": round(total["fiber"], 1),
        }
        return [cal_min, cal_max], macros, matched, unmatched

    def build_reply(self, items, calories, protein, today, budget_left, lang):
        """Build the reply text deterministically from the EXACT numbers, in the
        target language. This replaces the model's reply so the sentence numbers
        always match the structured data — and removes any need to translate."""
        # 1. items -> readable text, e.g. "3 roti, 1 rajma"
        parts = [f"{int(it.get('qty', 1)) if float(it.get('qty', 1)).is_integer() else it.get('qty', 1)} {it.get('name', '')}"
                 for it in items]
        items_text = ", ".join(parts) if parts else "meal"

        cmin, cmax = calories
        tmin, tmax = today

        # 2. a short verdict for a bit of personality (based on the numbers)
        verdict = {
            "english":  {"hi": " Solid protein.", "heavy": " Heavy meal — go light next.", "ok": ""},
            "hindi":    {"hi": " प्रोटीन बढ़िया है।", "heavy": " भारी मील — अगला हल्का।", "ok": ""},
            "hinglish": {"hi": " Protein solid hai.", "heavy": " Heavy meal — agla light rakhna.", "ok": ""},
        }[lang]
        if protein >= 25:
            v = verdict["hi"]
        elif cmax >= 800:
            v = verdict["heavy"]
        else:
            v = verdict["ok"]

        # 3. budget clause only if a budget is set
        if budget_left is not None:
            bmin, bmax = budget_left
            budget_clause = {
                "hindi":    f" बजट बचा: ~{bmin}-{bmax}।",
                "hinglish": f" Budget bacha: ~{bmin}-{bmax}.",
                "english":  f" Budget left: ~{bmin}-{bmax}.",
            }[lang]
        else:
            budget_clause = ""

        # 4. fill the per-language template with EXACT numbers
        if lang == "hindi":
            reply = (f"{items_text} = ~{cmin}-{cmax} कैलोरी, प्रोटीन {protein}g। "
                     f"आज तक: ~{tmin}-{tmax}।{budget_clause}{v}")
        elif lang == "hinglish":
            reply = (f"{items_text} = ~{cmin}-{cmax} cal, protein {protein}g. "
                     f"Total aaj: ~{tmin}-{tmax}.{budget_clause}{v}")
        else:  # english
            reply = (f"{items_text} = ~{cmin}-{cmax} cal, protein {protein}g. "
                     f"Today: ~{tmin}-{tmax}.{budget_clause}{v}")
        return reply

    def process(self, model_output, user_input, context, translate_fn=None):
        """Take the model's parsed JSON output and return a corrected version
        with EXACT calories/macros, recomputed totals, and a freshly-built reply.

        context = {"total_cal_so_far": int, "budget": int}
        translate_fn = kept for API compatibility; no longer needed because the
                       reply is built directly in the target language.
        """
        out = dict(model_output)  # shallow copy
        items = out.get("items", [])

        # 1. EXACT nutrition from CSV (override the model's guesses)
        cal_range, macros, matched, unmatched = self.compute_exact(items)
        if matched:  # only override if we matched at least one item
            out["calories"] = cal_range
            out.update(macros)

        # 2. Recompute running totals from exact calories + context
        prev = context.get("total_cal_so_far", 0) or 0
        budget = context.get("budget")          # may be None if user hasn't set one
        today = [prev + out["calories"][0], prev + out["calories"][1]]
        out["today_total"] = today
        if budget is not None:
            out["budget_left"] = [budget - today[1], budget - today[0]]
        else:
            out["budget_left"] = None           # no budget set -> no "budget left"

        # 3. Build the reply ourselves in the target language with EXACT numbers
        #    (this fixes both wrong numbers AND wrong language — no translate needed)
        target_lang = detect_language(user_input)
        if matched:
            out["reply"] = self.build_reply(
                items, out["calories"], out["protein_g"],
                out["today_total"], out["budget_left"], target_lang)
        # else: keep the model's reply (e.g. a query with no food items)

        out["_meta"] = {
            "target_lang": target_lang,
            "matched_items": matched,
            "unmatched_items": unmatched,
        }
        return out


# ----------------------------------------------------------------------
# Demo / self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys, json
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    hp = HybridProcessor()

    print("=" * 60)
    print("DEMO 1: The '3 roti + rajma' case (model said 12g protein)")
    print("=" * 60)

    # What the MODEL produced (from the Colab test — wrong numbers)
    model_said = {
        "items": [
            {"name": "roti", "qty": 3, "unit": "piece"},
            {"name": "rajma", "qty": 1, "unit": "bowl"},
        ],
        "calories": [280, 360],
        "protein_g": 12,
        "carbs_g": 42,
        "fat_g": 8,
        "fiber_g": 0,
        "reply": "3 roti aur rajma = 280-360 cal, protein 12g. Budget bacha hai.",
    }
    context = {"total_cal_so_far": 0, "budget": 2000}
    user_input = "abhi maine 3 roti aur ek bowl rajma khaya"

    fixed = hp.process(model_said, user_input, context)

    print("\nMODEL said:")
    print(f"  calories: {model_said['calories']}  protein: {model_said['protein_g']}g")
    print("\nHYBRID (CSV-corrected):")
    print(f"  calories: {fixed['calories']}  protein: {fixed['protein_g']}g")
    print(f"  carbs: {fixed['carbs_g']}g  fat: {fixed['fat_g']}g  fiber: {fixed['fiber_g']}g")
    print(f"  today_total: {fixed['today_total']}  budget_left: {fixed['budget_left']}")
    print(f"  matched: {fixed['_meta']['matched_items']}")
    print(f"  language: target={fixed['_meta']['target_lang']} reply={fixed['_meta']['reply_lang']} ok={fixed['_meta']['lang_ok']}")

    print("\n" + "=" * 60)
    print("DEMO 2: Language mismatch + translate fallback")
    print("=" * 60)

    # Model replied in English but user wrote Hinglish
    model_said2 = {
        "items": [{"name": "samosa", "qty": 2, "unit": "piece"}],
        "calories": [380, 440], "protein_g": 8, "carbs_g": 44, "fat_g": 22, "fiber_g": 3,
        "reply": "2 samosa = 400 cal. You have 1600 calories left for today.",
    }
    user2 = "shaam ko 2 samose kha liye"

    # fake translate_fn (at runtime this is a 2nd model call)
    def fake_translate(text, target):
        return "2 samose = ~400 cal. Aaj 1600 cal bacha hai bhai."

    fixed2 = hp.process(model_said2, user2, {"total_cal_so_far": 0, "budget": 2000},
                        translate_fn=fake_translate)
    print(f"\nUser (hinglish): {user2}")
    print(f"Model reply (english): {model_said2['reply']}")
    print(f"Detected mismatch: target={fixed2['_meta']['target_lang']}, reply={fixed2['_meta']['reply_lang']}")
    print(f"After translate: {fixed2['reply']}")
    print(f"  translated flag: {fixed2['_meta'].get('translated', False)}")

    print("\n" + "=" * 60)
    print("DEMO 3: Exact-match sanity check on a few foods")
    print("=" * 60)
    for name, qty in [("roti", 3), ("rajma", 1), ("butter chicken", 1), ("dal makhani", 1)]:
        info = hp.db.lookup(name)
        if info:
            print(f"  {qty} x {name:16s} -> {int(info['cal']*qty)} cal, {info['protein']*qty:.1f}g protein")
