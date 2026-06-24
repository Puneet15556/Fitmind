"""
Programmatic example generator for FitMind training data.

YOU PROVIDE:
  - Sentence templates per language/meal-type with {placeholders}
  - Reply templates per language with {placeholders}

SCRIPT DOES:
  - Iterates over nutrition.csv (348 foods)
  - Picks random quantities, meal types, memory contexts
  - Computes ACCURATE calories/protein/carbs from CSV
  - Fills templates with proper math
  - Outputs valid JSONL training examples

HOW TO ADD A NEW EXAMPLE PATTERN:
  Just add a dict to TEMPLATES list with:
    lang, meal_type, input_patterns (list), reply_pattern

Run: python scripts/generate_examples.py
Output: data/processed/generated_examples.jsonl
"""

import csv
import json
import random
import sys
from pathlib import Path

# Force UTF-8 console output on Windows
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

random.seed(42)  # reproducible

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
NUTRITION_CSV = DATA_DIR / "nutrition.csv"
OUT_JSONL = DATA_DIR / "generated_examples.jsonl"

# ============================================================
# CALORIE RANGE LOGIC
# ============================================================
# CSV has single values. Real-world portions vary ±15%.
# So we convert "200 cal" → [170, 230].
RANGE_PCT = 0.15

def to_range(value, n_servings=1):
    """Convert single value × servings → (min, max) realistic range."""
    total = value * n_servings
    return (int(total * (1 - RANGE_PCT)), int(total * (1 + RANGE_PCT)))


def round_macro(value, n_servings=1):
    """Round macro to nearest 0.5g."""
    return round(value * n_servings * 2) / 2


# ============================================================
# QUANTITY VARIATIONS (per food category)
# ============================================================
# Different foods have different realistic quantities.
QTY_VARIATIONS = {
    "bread":     [1, 2, 3, 4],
    "rice":      [1, 1, 2],          # weighted toward 1
    "dal":       [1, 1, 2],
    "sabzi":     [1, 1, 2],
    "nonveg":    [1, 1, 2],
    "breakfast": [1, 1, 2],
    "snack":     [1, 2, 2, 3],
    "sweet":     [1, 1, 2, 3],
    "dairy":     [1, 1, 2],
    "drink":     [1, 1, 2],
    "fruit":     [1, 1, 2],
    "nuts":      [1, 1, 2],
    "vegetable": [1, 1, 2],
    "salad":     [1, 1, 1],
}

# Unit text per category (for natural phrasing)
UNIT_BY_CAT = {
    "bread":     "piece",
    "rice":      "bowl",
    "dal":       "bowl",
    "sabzi":     "bowl",
    "nonveg":    "bowl",
    "breakfast": "plate",
    "snack":     "piece",
    "sweet":     "piece",
    "dairy":     "glass",
    "drink":     "glass",
    "fruit":     "piece",
    "nuts":      "handful",
    "vegetable": "piece",
    "salad":     "plate",
}

# ============================================================
# MEMORY CONTEXT SCENARIOS
# ============================================================
# Random "earlier today" states to teach memory awareness.
MEMORY_SCENARIOS = [
    # Empty (morning, first meal)
    {"today_meals": [], "total_cal_so_far": 0, "budget": 2000},
    {"today_meals": [], "total_cal_so_far": 0, "budget": 2200},
    {"today_meals": [], "total_cal_so_far": 0, "budget": 1800},
    # Light morning
    {"today_meals": [{"meal": "tea + biscuits", "cal": [180, 220]}],
     "total_cal_so_far": 200, "budget": 2000},
    {"today_meals": [{"meal": "oats", "cal": [160, 200]}],
     "total_cal_so_far": 180, "budget": 2200},
    # Mid-day
    {"today_meals": [
        {"meal": "3 paratha", "cal": [510, 660]},
        {"meal": "2 roti + dal", "cal": [300, 370]}],
     "total_cal_so_far": 920, "budget": 2000},
    {"today_meals": [
        {"meal": "oats + protein shake", "cal": [480, 480]},
        {"meal": "chicken salad", "cal": [320, 320]}],
     "total_cal_so_far": 800, "budget": 2500},
    # Heavy day
    {"today_meals": [
        {"meal": "biryani", "cal": [580, 580]},
        {"meal": "samosa", "cal": [200, 220]}],
     "total_cal_so_far": 800, "budget": 1800},
]


# ============================================================
# TEMPLATES — THIS IS WHERE YOU ADD PATTERNS
# ============================================================
# Each template has:
#   - lang:           "english" / "hindi" / "hinglish"
#   - meal_type:      breakfast / lunch / snack / dinner
#   - input_patterns: list of strings with {qty}, {food}, {unit} placeholders
#                     script picks one randomly per generation
#   - reply_pattern:  string with {qty} {food} {cal_min} {cal_max} {protein}
#                                  {today_min} {today_max} {budget_min} {budget_max}
# ============================================================

TEMPLATES = [
    # -------- HINGLISH BREAKFAST --------
    {
        "lang": "hinglish",
        "meal_type": "breakfast",
        "input_patterns": [
            "subah {qty} {food} khaya",
            "breakfast mein {qty} {food} khaya",
            "morning ko {qty} {food} le liya",
            "nashte mein {qty} {food}",
            "aaj subah {qty} {food} tha",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal, protein {protein}g. Total: ~{today_min}-{today_max}. Budget bacha: ~{budget_min}-{budget_max}."
    },
    # -------- HINGLISH LUNCH --------
    {
        "lang": "hinglish",
        "meal_type": "lunch",
        "input_patterns": [
            "lunch mein {qty} {food} khaya",
            "dopahar ko {qty} {food}",
            "{qty} {food} lunch mein le liya",
            "aaj lunch tha {qty} {food}",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal. Total aaj: ~{today_min}-{today_max}. Budget bacha: ~{budget_min}-{budget_max}."
    },
    # -------- HINGLISH SNACK --------
    {
        "lang": "hinglish",
        "meal_type": "snack",
        "input_patterns": [
            "shaam ko {qty} {food} kha liye",
            "snack mein {qty} {food}",
            "{qty} {food} chai ke saath",
            "abhi {qty} {food} khaya",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal. Total: ~{today_min}-{today_max}. Budget bacha: ~{budget_min}-{budget_max}."
    },
    # -------- HINGLISH DINNER --------
    {
        "lang": "hinglish",
        "meal_type": "dinner",
        "input_patterns": [
            "dinner mein {qty} {food}",
            "raat ko {qty} {food} khaya",
            "{qty} {food} dinner mein le liya",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal. Total aaj: ~{today_min}-{today_max}. Budget bacha: ~{budget_min}-{budget_max}."
    },

    # -------- ENGLISH BREAKFAST --------
    {
        "lang": "english",
        "meal_type": "breakfast",
        "input_patterns": [
            "I had {qty} {food} for breakfast",
            "Breakfast was {qty} {food}",
            "Ate {qty} {food} in the morning",
            "{qty} {food} for breakfast today",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal, protein {protein}g. Total: ~{today_min}-{today_max} cal. Budget left: ~{budget_min}-{budget_max} cal."
    },
    # -------- ENGLISH LUNCH --------
    {
        "lang": "english",
        "meal_type": "lunch",
        "input_patterns": [
            "I had {qty} {food} for lunch",
            "Lunch was {qty} {food}",
            "Ate {qty} {food} at lunch",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal. Today total: ~{today_min}-{today_max}. Budget left: ~{budget_min}-{budget_max}."
    },
    # -------- ENGLISH SNACK --------
    {
        "lang": "english",
        "meal_type": "snack",
        "input_patterns": [
            "Snacked on {qty} {food}",
            "Just had {qty} {food}",
            "{qty} {food} as a snack",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal. Total: ~{today_min}-{today_max}. Budget left: ~{budget_min}-{budget_max}."
    },
    # -------- ENGLISH DINNER --------
    {
        "lang": "english",
        "meal_type": "dinner",
        "input_patterns": [
            "Dinner: {qty} {food}",
            "Had {qty} {food} for dinner",
            "{qty} {food} tonight",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} cal. Today total: ~{today_min}-{today_max}. Budget left: ~{budget_min}-{budget_max}."
    },

    # -------- HINDI BREAKFAST --------
    {
        "lang": "hindi",
        "meal_type": "breakfast",
        "input_patterns": [
            "नाश्ते में {qty} {food} खाया",
            "सुबह {qty} {food} लिया",
            "{qty} {food} नाश्ता था",
        ],
        "reply_pattern": "{qty} {food} = लगभग {cal_min}-{cal_max} कैलोरी, प्रोटीन {protein}g। कुल: ~{today_min}-{today_max}। बजट बचा: ~{budget_min}-{budget_max}।"
    },
    # -------- HINDI LUNCH --------
    {
        "lang": "hindi",
        "meal_type": "lunch",
        "input_patterns": [
            "दोपहर में {qty} {food} खाया",
            "लंच में {qty} {food} लिया",
            "{qty} {food} लंच में था",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} कैलोरी। कुल आज: ~{today_min}-{today_max}। बजट बचा: ~{budget_min}-{budget_max}।"
    },
    # -------- HINDI SNACK --------
    {
        "lang": "hindi",
        "meal_type": "snack",
        "input_patterns": [
            "शाम को {qty} {food} खाया",
            "अभी {qty} {food} लिया",
            "{qty} {food} स्नैक में",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} कैलोरी। कुल: ~{today_min}-{today_max}। बजट बचा: ~{budget_min}-{budget_max}।"
    },
    # -------- HINDI DINNER --------
    {
        "lang": "hindi",
        "meal_type": "dinner",
        "input_patterns": [
            "रात में {qty} {food} खाया",
            "डिनर में {qty} {food}",
            "{qty} {food} रात को था",
        ],
        "reply_pattern": "{qty} {food} = ~{cal_min}-{cal_max} कैलोरी। कुल आज: ~{today_min}-{today_max}। बजट बचा: ~{budget_min}-{budget_max}।"
    },
]


# ============================================================
# GENERATOR
# ============================================================

def load_nutrition():
    """Load nutrition CSV into list of dicts."""
    foods = []
    with NUTRITION_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            foods.append({
                "name":     row["food_name"],
                "category": row["category"],
                "serving":  row["typical_serving"],
                "cal":      float(row["calories"]),
                "protein":  float(row["protein_g"]),
                "carbs":    float(row["carbs_g"]),
                "fat":      float(row["fat_g"]),
                "fiber":    float(row["fiber_g"]),
            })
    return foods


def make_example(food, template):
    """Build one training example for given food + template."""
    # 1. Pick realistic quantity for category
    qty = random.choice(QTY_VARIATIONS.get(food["category"], [1]))
    unit = UNIT_BY_CAT.get(food["category"], "piece")

    # 2. Pick memory context
    memory = random.choice(MEMORY_SCENARIOS)

    # 3. Compute accurate nutrition for this qty
    cal_min, cal_max = to_range(food["cal"], qty)
    protein = round_macro(food["protein"], qty)
    carbs   = round_macro(food["carbs"], qty)
    fat     = round_macro(food["fat"], qty)
    fiber   = round_macro(food["fiber"], qty)

    # 4. Compute new totals
    today_min = memory["total_cal_so_far"] + cal_min
    today_max = memory["total_cal_so_far"] + cal_max
    budget_min = memory["budget"] - today_max
    budget_max = memory["budget"] - today_min

    # 5. Fill input pattern
    input_text = random.choice(template["input_patterns"]).format(
        qty=qty, food=food["name"], unit=unit
    )

    # 6. Fill reply pattern
    reply = template["reply_pattern"].format(
        qty=qty, food=food["name"], unit=unit,
        cal_min=cal_min, cal_max=cal_max,
        protein=protein,
        today_min=today_min, today_max=today_max,
        budget_min=budget_min, budget_max=budget_max,
    )

    return {
        "lang":      template["lang"],
        "meal_type": template["meal_type"],
        "context":   memory,
        "input":     input_text,
        "output": {
            "items": [{"name": food["name"], "qty": qty, "unit": unit}],
            "calories":     [cal_min, cal_max],
            "protein_g":    protein,
            "carbs_g":      carbs,
            "fat_g":        fat,
            "fiber_g":      fiber,
            "today_total":  [today_min, today_max],
            "budget_left":  [budget_min, budget_max],
            "reply":        reply,
        }
    }


# Which categories make sense per meal_type
MEAL_TYPE_CATEGORIES = {
    "breakfast": ["breakfast", "bread", "dairy", "fruit", "drink"],
    "lunch":     ["rice", "dal", "sabzi", "bread", "nonveg", "salad"],
    "dinner":    ["rice", "dal", "sabzi", "bread", "nonveg", "salad"],
    "snack":     ["snack", "sweet", "drink", "fruit", "nuts", "dairy", "vegetable"],
}


def generate_all(per_template=25):
    """Generate per_template examples per template."""
    foods = load_nutrition()
    examples = []

    for tpl in TEMPLATES:
        # Filter foods to ones that match this meal_type
        valid_cats = MEAL_TYPE_CATEGORIES.get(tpl["meal_type"], [])
        candidates = [f for f in foods if f["category"] in valid_cats]
        if not candidates:
            continue

        # Random sample
        sample = random.sample(candidates, min(per_template, len(candidates)))
        for food in sample:
            examples.append(make_example(food, tpl))

    return examples


if __name__ == "__main__":
    examples = generate_all(per_template=25)

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Generated {len(examples)} examples -> {OUT_JSONL}")

    # Stats
    from collections import Counter
    lang = Counter(e["lang"] for e in examples)
    meal = Counter(e["meal_type"] for e in examples)
    print(f"\nLanguage breakdown:")
    for k, v in lang.most_common():
        print(f"  {k:10s}: {v}")
    print(f"\nMeal type breakdown:")
    for k, v in meal.most_common():
        print(f"  {k:12s}: {v}")

    # Sample preview
    print(f"\n--- 3 SAMPLE EXAMPLES ---")
    for ex in random.sample(examples, 3):
        print(f"\n[{ex['lang']} / {ex['meal_type']}]")
        print(f"INPUT:  {ex['input']}")
        print(f"REPLY:  {ex['output']['reply']}")
        print(f"CALS:   {ex['output']['calories']}")
