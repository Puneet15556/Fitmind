"""
Multi-item combo meal generator for FitMind.

Generates realistic Indian meal combinations (thali, breakfast plate, etc.)
where MULTIPLE foods are eaten together — e.g. "2 roti + dal + sabzi".

The script:
  - Defines realistic combo "recipes" (which food categories go together)
  - Picks actual foods from nutrition.csv for each slot
  - SUMS calories/protein/carbs across all items (accurate math)
  - Builds natural multi-item sentences in 3 languages
  - Outputs JSONL training examples

You don't write anything — just run it.
Run: python scripts/generate_combos.py
Output: data/processed/combo_examples.jsonl
"""

import csv
import json
import random
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

random.seed(123)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
NUTRITION_CSV = DATA_DIR / "nutrition.csv"
OUT_JSONL = DATA_DIR / "combo_examples.jsonl"

RANGE_PCT = 0.15

# ============================================================
# COMBO RECIPES — which categories make a realistic meal
# Each slot = (category, possible quantities)
# ============================================================
COMBO_RECIPES = {
    "north_thali": {
        "meal_type": "lunch",
        "slots": [
            ("bread", [2, 3, 4]),     # roti/naan
            ("dal",   [1]),
            ("sabzi", [1]),
            ("dairy", [1]),           # curd
        ],
        "dairy_filter": ["curd", "dahi low fat", "buttermilk"],
    },
    "rice_combo": {
        "meal_type": "lunch",
        "slots": [
            ("rice",  [1, 2]),
            ("dal",   [1]),
            ("sabzi", [1]),
        ],
    },
    "gym_meal": {
        "meal_type": "lunch",
        "slots": [
            ("nonveg", [1]),          # chicken
            ("rice",   [1]),
            ("salad",  [1]),
        ],
        "nonveg_filter": ["chicken breast grilled", "chicken breast boiled",
                          "fish grilled", "tandoori chicken"],
    },
    "south_breakfast": {
        "meal_type": "breakfast",
        "slots": [
            ("breakfast", [1, 2]),    # dosa/idli
            ("drink",     [1]),       # filter coffee
        ],
        "breakfast_filter": ["dosa plain", "dosa masala", "idli", "uttapam",
                            "medu vada", "rava dosa", "masala dosa"],
        "drink_filter": ["filter coffee", "coffee milk", "tea milk"],
    },
    "north_breakfast": {
        "meal_type": "breakfast",
        "slots": [
            ("bread", [2, 3]),        # paratha
            ("dairy", [1]),           # curd
            ("drink", [1]),           # chai
        ],
        "bread_filter": ["paratha plain", "paratha aloo", "paratha butter", "thepla"],
        "dairy_filter": ["curd", "dahi low fat"],
        "drink_filter": ["tea milk", "masala chai"],
    },
    "street_combo": {
        "meal_type": "snack",
        "slots": [
            ("snack", [1, 2]),
            ("drink", [1]),
        ],
        "drink_filter": ["coke", "pepsi", "sprite", "nimbu pani sweet", "lassi sweet"],
    },
    "dinner_light": {
        "meal_type": "dinner",
        "slots": [
            ("bread", [2]),
            ("sabzi", [1]),
            ("salad", [1]),
        ],
    },
    "protein_combo": {
        "meal_type": "snack",
        "slots": [
            ("drink", [1]),           # protein shake
            ("fruit", [1]),           # banana
            ("nuts",  [1]),
        ],
        "drink_filter": ["protein shake", "smoothie protein", "milk toned"],
        "fruit_filter": ["banana", "apple"],
    },
}

# ============================================================
# SENTENCE BUILDERS (join items naturally per language)
# ============================================================
JOINERS = {
    "english":  [" and ", ", ", " with "],
    "hindi":    [" और ", ", "],
    "hinglish": [" aur ", ", ", " ke saath "],
}

INTRO = {
    "english": {
        "lunch":     ["For lunch I had ", "Lunch was ", "Ate "],
        "breakfast": ["For breakfast I had ", "Breakfast: ", "Morning I had "],
        "dinner":    ["For dinner ", "Dinner was ", "Tonight I had "],
        "snack":     ["Snacked on ", "Had ", ""],
    },
    "hindi": {
        "lunch":     ["दोपहर में ", "लंच में मैंने ", ""],
        "breakfast": ["नाश्ते में ", "सुबह मैंने ", ""],
        "dinner":    ["रात में ", "डिनर में ", ""],
        "snack":     ["शाम को ", "मैंने ", ""],
    },
    "hinglish": {
        "lunch":     ["lunch mein ", "dopahar ko ", ""],
        "breakfast": ["subah ", "breakfast mein ", "nashte mein "],
        "dinner":    ["dinner mein ", "raat ko ", ""],
        "snack":     ["shaam ko ", "abhi ", ""],
    },
}

OUTRO = {
    "english":  ["", " for the meal", " today"],
    "hindi":    [" खाया", " लिया", ""],
    "hinglish": [" khaya", " le liya", ""],
}

REPLY_TEMPLATE = {
    "english":  "{items_text} = ~{cal_min}-{cal_max} cal, protein {protein}g. Today total: ~{today_min}-{today_max}. Budget left: ~{budget_min}-{budget_max}.{verdict}",
    "hindi":    "{items_text} = ~{cal_min}-{cal_max} कैलोरी, प्रोटीन {protein}g। कुल आज: ~{today_min}-{today_max}। बजट बचा: ~{budget_min}-{budget_max}।{verdict}",
    "hinglish": "{items_text} = ~{cal_min}-{cal_max} cal, protein {protein}g. Total aaj: ~{today_min}-{today_max}. Budget bacha: ~{budget_min}-{budget_max}.{verdict}",
}

# Verdicts based on protein/calories
VERDICTS = {
    "english": {
        "high_protein": " Solid protein meal.",
        "heavy":        " Heavy meal — keep next one light.",
        "balanced":     " Well-balanced.",
    },
    "hindi": {
        "high_protein": " प्रोटीन बढ़िया है।",
        "heavy":        " भारी मील — अगला हल्का रखो।",
        "balanced":     " संतुलित मील।",
    },
    "hinglish": {
        "high_protein": " Protein solid hai bhai.",
        "heavy":        " Heavy meal — agla light rakhna.",
        "balanced":     " Balanced hai.",
    },
}

MEMORY_SCENARIOS = [
    {"today_meals": [], "total_cal_so_far": 0, "budget": 2000},
    {"today_meals": [], "total_cal_so_far": 0, "budget": 2200},
    {"today_meals": [{"meal": "breakfast", "cal": [300, 400]}],
     "total_cal_so_far": 350, "budget": 2000},
    {"today_meals": [
        {"meal": "breakfast", "cal": [300, 400]},
        {"meal": "snack", "cal": [150, 200]}],
     "total_cal_so_far": 525, "budget": 2200},
]


def load_nutrition():
    by_cat = {}
    by_name = {}
    with NUTRITION_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            food = {
                "name":    row["food_name"],
                "category": row["category"],
                "cal":     float(row["calories"]),
                "protein": float(row["protein_g"]),
                "carbs":   float(row["carbs_g"]),
                "fat":     float(row["fat_g"]),
                "fiber":   float(row["fiber_g"]),
            }
            by_cat.setdefault(food["category"], []).append(food)
            by_name[food["name"]] = food
    return by_cat, by_name


def pick_food(by_cat, category, recipe):
    """Pick a food from category, respecting any filter in recipe."""
    filter_key = f"{category}_filter"
    candidates = by_cat.get(category, [])
    if filter_key in recipe:
        allowed = recipe[filter_key]
        filtered = [f for f in candidates if f["name"] in allowed]
        if filtered:
            candidates = filtered
    return random.choice(candidates) if candidates else None


def make_combo(recipe_name, recipe, by_cat, lang):
    """Build one multi-item combo example."""
    items = []
    total_cal = total_protein = total_carbs = total_fat = total_fiber = 0.0

    for category, qtys in recipe["slots"]:
        food = pick_food(by_cat, category, recipe)
        if not food:
            continue
        qty = random.choice(qtys)
        items.append({"food": food, "qty": qty})
        total_cal     += food["cal"]     * qty
        total_protein += food["protein"] * qty
        total_carbs   += food["carbs"]   * qty
        total_fat      += food["fat"]     * qty
        total_fiber   += food["fiber"]   * qty

    if len(items) < 2:
        return None  # need at least 2 items for a combo

    # Ranges
    cal_min = int(total_cal * (1 - RANGE_PCT))
    cal_max = int(total_cal * (1 + RANGE_PCT))
    protein = round(total_protein * 2) / 2
    carbs   = round(total_carbs * 2) / 2
    fat     = round(total_fat * 2) / 2
    fiber   = round(total_fiber * 2) / 2

    # Memory + totals
    memory = random.choice(MEMORY_SCENARIOS)
    today_min = memory["total_cal_so_far"] + cal_min
    today_max = memory["total_cal_so_far"] + cal_max
    budget_min = memory["budget"] - today_max
    budget_max = memory["budget"] - today_min

    meal_type = recipe["meal_type"]

    # Build input sentence: "2 roti aur dal aur sabzi"
    parts = [f"{it['qty']} {it['food']['name']}" for it in items]
    joiner = random.choice(JOINERS[lang])
    items_phrase = joiner.join(parts)
    intro = random.choice(INTRO[lang][meal_type])
    outro = random.choice(OUTRO[lang])
    input_text = f"{intro}{items_phrase}{outro}".strip()

    # Items text for reply (cleaner join)
    items_text = ", ".join(parts)

    # Pick verdict
    if protein >= 25:
        verdict = VERDICTS[lang]["high_protein"]
    elif cal_max >= 800:
        verdict = VERDICTS[lang]["heavy"]
    else:
        verdict = VERDICTS[lang]["balanced"]

    reply = REPLY_TEMPLATE[lang].format(
        items_text=items_text,
        cal_min=cal_min, cal_max=cal_max, protein=protein,
        today_min=today_min, today_max=today_max,
        budget_min=budget_min, budget_max=budget_max,
        verdict=verdict,
    )

    return {
        "lang": lang,
        "meal_type": meal_type,
        "combo": recipe_name,
        "context": memory,
        "input": input_text,
        "output": {
            "items": [
                {"name": it["food"]["name"], "qty": it["qty"],
                 "unit": "serving"} for it in items
            ],
            "calories":    [cal_min, cal_max],
            "protein_g":   protein,
            "carbs_g":     carbs,
            "fat_g":       fat,
            "fiber_g":     fiber,
            "today_total": [today_min, today_max],
            "budget_left": [budget_min, budget_max],
            "reply":       reply,
        }
    }


def generate_all(per_recipe_per_lang=12):
    by_cat, _ = load_nutrition()
    examples = []
    for recipe_name, recipe in COMBO_RECIPES.items():
        for lang in ["english", "hindi", "hinglish"]:
            made = 0
            attempts = 0
            while made < per_recipe_per_lang and attempts < per_recipe_per_lang * 4:
                attempts += 1
                ex = make_combo(recipe_name, recipe, by_cat, lang)
                if ex:
                    examples.append(ex)
                    made += 1
    return examples


if __name__ == "__main__":
    examples = generate_all(per_recipe_per_lang=12)

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Generated {len(examples)} combo examples -> {OUT_JSONL}")

    from collections import Counter
    lang = Counter(e["lang"] for e in examples)
    combo = Counter(e["combo"] for e in examples)
    print(f"\nLanguage breakdown:")
    for k, v in lang.most_common():
        print(f"  {k:10s}: {v}")
    print(f"\nCombo type breakdown:")
    for k, v in combo.most_common():
        print(f"  {k:18s}: {v}")

    print(f"\n--- 4 SAMPLE COMBOS ---")
    for ex in random.sample(examples, 4):
        print(f"\n[{ex['lang']} / {ex['combo']}]")
        print(f"INPUT:  {ex['input']}")
        print(f"REPLY:  {ex['output']['reply']}")
