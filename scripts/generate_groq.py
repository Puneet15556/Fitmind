"""
Groq Llama-70B distillation script for FitMind.

This is the DATA DISTILLATION step:
  - Teacher: Llama-3.3-70B (via Groq, free)
  - Generates NATURAL, context-aware food-logging examples
  - Each example carries memory context (previous meals + running total)
  - Llama is told the exact nutrition facts so it doesn't hallucinate calories

HOW TO RUN:
  1. Get free API key from console.groq.com
  2. Set it:   (PowerShell)  $env:GROQ_API_KEY = "gsk_xxxx"
               (or pass via --key argument)
  3. Run:      python scripts/generate_groq.py --n 60

Output: data/processed/groq_examples.jsonl
"""

import csv
import json
import os
import random
import sys
import argparse
from pathlib import Path

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Load .env file (GROQ_API_KEY etc.) from project root
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # dotenv optional; env var can still be set manually

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
NUTRITION_CSV = DATA_DIR / "nutrition.csv"
GOLD_JSONL = DATA_DIR / "gold_examples.jsonl"
OUT_JSONL = DATA_DIR / "groq_examples.jsonl"

MODEL = "llama-3.3-70b-versatile"

# ============================================================
# Load nutrition facts — we GIVE these to Llama so calories are accurate
# ============================================================
def load_nutrition():
    foods = []
    with NUTRITION_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            foods.append(row)
    return foods


def load_gold_samples(n=4):
    """Load a few gold examples to show Llama the desired format."""
    examples = []
    with GOLD_JSONL.open(encoding="utf-8") as f:
        for line in f:
            examples.append(json.loads(line))
    return random.sample(examples, min(n, len(examples)))


# ============================================================
# Build the prompt for Llama-70B
# ============================================================
RICH_INSTRUCTIONS = """
EXTRA VARIETY (IMPORTANT for this batch):
- PREPARATION / OIL variations: many inputs should mention how the food was made,
  and you MUST adjust calories accordingly:
    * "oily", "extra oil", "deep fried", "extra ghee", "butter wala", "malai", "fried"
      -> increase calories ~20-40% above the base value.
    * "less oil", "no oil", "steamed", "grilled", "roasted", "boiled", "tandoori", "dry"
      -> decrease calories ~15-25% below the base value.
  Examples: "oily masala dosa", "extra ghee paratha", "less oil bhindi",
            "grilled paneer instead of fried", "deep fried pakora".
- MORE COMBINATIONS: at least half the examples should have 2-3 food items together
  (a realistic plate/thali), e.g. "2 roti + dal + sabzi", "dosa with extra sambar and chutney".
- Mention the oil/prep reasoning briefly in the reply
  (e.g. "oily dosa so higher end ~300 cal", "grilled so lighter").
"""


def build_prompt(nutrition_subset, gold_samples, lang, batch_size=5, style="default"):
    # Format nutrition facts as a reference table
    facts = "\n".join(
        f"- {f['food_name']}: {f['calories']} cal, {f['protein_g']}g protein, "
        f"{f['carbs_g']}g carbs, {f['fat_g']}g fat (per {f['typical_serving']})"
        for f in nutrition_subset
    )

    # Show format via gold examples
    examples_text = "\n\n".join(
        json.dumps(ex, ensure_ascii=False, indent=2) for ex in gold_samples
    )

    lang_instruction = {
        "english": "Write the 'input' and 'reply' in natural English.",
        "hindi": "Write the 'input' and 'reply' in natural Hindi (Devanagari script).",
        "hinglish": "Write the 'input' and 'reply' in natural Hinglish (Hindi+English mix, Roman script) — how young Indian gym-goers actually text.",
    }[lang]

    strict_lang = {
        "english": "PURE ENGLISH ONLY. No Hindi words like 'khaya', 'maine', 'bacha'. Use 'I had', 'ate', 'budget left'.",
        "hindi": "PURE HINDI in Devanagari script (मैंने, खाया, कैलोरी). No Roman/English words for the food logging.",
        "hinglish": "HINGLISH — Hindi+English mixed in Roman script (e.g. 'abhi maine 2 roti khaya', 'budget bacha'). How Indian gym-goers actually text.",
    }[lang]

    rich_block = RICH_INSTRUCTIONS if style == "rich" else ""

    prompt = f"""You are generating training data for a calorie-tracking AI for Indian gym users.

NUTRITION FACTS (use these EXACT values — do not invent calories):
{facts}

FORMAT — here are example training items:
{examples_text}

YOUR TASK:
Generate {batch_size} NEW, realistic training examples as a JSON array.

LANGUAGE (CRITICAL): {strict_lang}

RULES:
1. Each example must have a "context" simulating earlier meals today:
   - Sometimes empty (first meal: today_meals=[], total_cal_so_far=0)
   - Sometimes 1-2 previous meals with a running "total_cal_so_far"
   - "budget" is usually 1800-2500
2. The "input" should sound like a real person logging food RIGHT NOW
   (e.g. "abhi maine ye khaya", "just had", casual tone, natural quantities).
3. MATH (do this carefully):
   - "calories" = [low, high] range (~±15% of the food's value × quantity)
   - "today_total" = [total_cal_so_far + calories_low, total_cal_so_far + calories_high]
   - "budget_left" = [budget - today_total_high, budget - today_total_low]
     IMPORTANT: budget_left MUST be [smaller_number, larger_number] (ascending order).
   - Sum protein_g, carbs_g, fat_g, fiber_g for the items.
4. The "reply" must be in the SAME language as input, mention the new meal's
   calories, the updated running total, and remaining budget. Short & natural.
5. Use ONLY foods from the nutrition facts above. Quantities can vary (1-4).
6. Output ONLY a valid JSON array of {batch_size} objects. No extra text.
{rich_block}
Generate now:"""
    return prompt


# ============================================================
# Call Groq + parse
# ============================================================
def generate_batch(client, nutrition, gold_samples, lang, batch_size=5, style="default"):
    subset = random.sample(nutrition, min(25, len(nutrition)))
    prompt = build_prompt(subset, gold_samples, lang, batch_size, style)

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,          # higher = more diverse phrasing
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content.strip()

    # Llama may wrap array in an object or return raw array
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # try to extract array
        start = text.find("[")
        end = text.rfind("]") + 1
        data = json.loads(text[start:end])

    # Normalize: could be {"examples": [...]} or [...] or {...}
    if isinstance(data, dict):
        # find the list value
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
        else:
            data = [data]
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=60,
                        help="total examples to generate (split across 3 languages)")
    parser.add_argument("--key", type=str, default=None,
                        help="Groq API key (or set GROQ_API_KEY env var)")
    parser.add_argument("--batch", type=int, default=5,
                        help="examples per API call")
    parser.add_argument("--name", type=str, default=None,
                        help="batch name -> saves to groq_<name>.jsonl (e.g. b2)")
    parser.add_argument("--style", type=str, default="default",
                        choices=["default", "rich"],
                        help="'rich' = oil/preparation variations + more multi-item combos")
    args = parser.parse_args()

    out_path = OUT_JSONL if not args.name else \
        DATA_DIR / f"groq_{args.name}.jsonl"

    api_key = args.key or os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "paste_your_gsk_key_here":
        print("ERROR: No valid Groq API key found.")
        print("Get one free at console.groq.com, then paste it into the .env file:")
        print('  fitmind/.env  ->  GROQ_API_KEY=gsk_xxxx')
        sys.exit(1)

    try:
        from groq import Groq
    except ImportError:
        print("ERROR: groq not installed. Run: pip install groq")
        sys.exit(1)

    client = Groq(api_key=api_key)
    nutrition = load_nutrition()

    all_examples = []
    langs = ["english", "hindi", "hinglish"]
    per_lang = args.n // 3
    calls_per_lang = max(1, per_lang // args.batch)

    for lang in langs:
        print(f"\n[{lang}] generating ~{calls_per_lang * args.batch} examples...")
        for i in range(calls_per_lang):
            gold = load_gold_samples(4)
            try:
                batch = generate_batch(client, nutrition, gold, lang, args.batch, args.style)
                # tag language + mark source
                for ex in batch:
                    ex["lang"] = lang
                    ex["source"] = "groq_llama70b"
                all_examples.extend(batch)
                print(f"  call {i+1}/{calls_per_lang}: +{len(batch)} (total {len(all_examples)})")
            except Exception as e:
                print(f"  call {i+1} FAILED: {e}")

    # Save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nDONE. {len(all_examples)} examples -> {out_path}")

    # Preview
    if all_examples:
        print("\n--- 2 SAMPLES ---")
        for ex in random.sample(all_examples, min(2, len(all_examples))):
            print(f"\n[{ex.get('lang')}]")
            print(f"INPUT: {ex.get('input')}")
            out = ex.get('output', {})
            print(f"REPLY: {out.get('reply')}")


if __name__ == "__main__":
    main()
