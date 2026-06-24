"""
Recommender — a deterministic constraint solver over the nutrition CSV.

Answers "what should I eat?" queries like:
   "250 cal me paneer kaise khau, 12g protein chahiye"
   "suggest chicken under 300 cal with 25g protein"

The model does NOT do the math. We:
  1. parse_constraints()  -> food family + calorie ceiling + protein floor
  2. recommend()          -> for each matching dish, compute the portion that
                             stays under the calorie ceiling, keep those that
                             still clear the protein floor, rank by protein.

Math (per dish): eat fraction q of one serving.
  calorie limit:  q <= max_cal / cal_per_serving
  protein floor:  protein_per_serving * q >= min_protein
  Best q = max_cal / cal_per_serving  (max protein at the calorie limit).
"""

import re

# words that aren't foods (so we don't pick them as the food family)
STOP = {"cal", "calorie", "calories", "kcal", "protein", "gram", "grams", "gm", "g",
        "me", "mein", "kaise", "khau", "khaau", "under", "with", "and", "ka", "ki",
        "ke", "chahiye", "want", "suggest", "give", "i", "a", "to", "for", "ho",
        "jaaye", "jaye", "mil", "exceed", "na", "kare", "only", "just"}


def parse_constraints(text, food_vocab):
    """Extract (food_query, max_cal, min_protein) from natural language.
    food_vocab = set of single words that appear in CSV food names."""
    t = text.lower()

    # calorie ceiling: "250 cal", "under 300 calorie", "300 kcal"
    max_cal = None
    m = re.search(r"(\d+)\s*(k?cal|calorie)", t)
    if m:
        max_cal = int(m.group(1))

    # protein floor: "12 g protein", "12gm protein", "protein 12"
    min_protein = None
    m = re.search(r"(\d+)\s*(?:g|gm|gram)s?\s*protein", t)
    if not m:
        m = re.search(r"protein\s*(?:of\s*)?(\d+)", t)
    if m:
        min_protein = int(m.group(1))

    # food family: the query word that matches a CSV food word
    food_query = None
    for w in re.findall(r"[a-z]+", t):
        if w in STOP:
            continue
        if w in food_vocab:
            food_query = w
            break

    return food_query, max_cal, min_protein


def _grams(serving):
    """Pull the gram amount out of a serving string like '1 plate (150g)'."""
    m = re.search(r"(\d+)\s*g", serving or "")
    return int(m.group(1)) if m else None


def recommend(food_query, max_cal, min_protein, db, top=3):
    """Return a ranked list of dishes + portions that fit the constraints."""
    if not food_query or not max_cal:
        return []
    min_protein = min_protein or 0
    out = []
    for name, info in db.by_name.items():
        if food_query not in name:           # same food family
            continue
        cal = info["cal"]
        if cal <= 0:
            continue
        q = max_cal / cal                    # max fraction under calorie ceiling
        q = min(q, 3.0)                       # don't suggest absurd portions
        protein_at_q = info["protein"] * q
        if protein_at_q < min_protein:       # can't hit protein floor -> skip
            continue
        g = _grams(info["serving"])
        out.append({
            "name": name,
            "serving": info["serving"],
            "portion": round(q, 2),                 # e.g. 0.78 of a serving
            "grams": round(g * q) if g else None,
            "calories": round(cal * q),
            "protein_g": round(protein_at_q, 1),
        })
    out.sort(key=lambda c: -c["protein_g"])  # most protein first
    return out[:top]


def build_reply(food_query, max_cal, min_protein, recs, lang="hinglish"):
    """Turn the recommendations into a chat reply in the user's language."""
    if not recs:
        none_msg = {
            "hindi":    f"{max_cal} कैलोरी में {min_protein}g प्रोटीन वाला {food_query} option नहीं मिला।",
            "hinglish": f"{max_cal} cal mein {min_protein}g protein wala {food_query} nahi mila bhai.",
            "english":  f"No {food_query} option fits {max_cal} cal with {min_protein}g protein.",
        }
        return none_msg.get(lang, none_msg["english"])

    lines = []
    for r in recs:
        port = f"{r['grams']}g" if r["grams"] else f"{r['portion']}x serving"
        lines.append(f"• {r['name']} (~{port}) → {r['calories']} cal, {r['protein_g']}g protein")
    head = {
        "hindi":    f"{max_cal} कैलोरी, {min_protein}g प्रोटीन के लिए:",
        "hinglish": f"{max_cal} cal mein {min_protein}g protein ke liye:",
        "english":  f"For {max_cal} cal with {min_protein}g protein:",
    }.get(lang)
    return head + "\n" + "\n".join(lines)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    from hybrid import NutritionDB

    db = NutritionDB()
    # build vocab of words that appear in food names
    vocab = set()
    for name in db.by_name:
        vocab.update(name.split())

    print("=== parse test ===")
    fq, mc, mp = parse_constraints("250 cal me paneer khau 12g protein chahiye", vocab)
    print(f"  food={fq} max_cal={mc} min_protein={mp}")
    assert fq == "paneer" and mc == 250 and mp == 12

    print("\n=== recommend: paneer, <=250 cal, >=12g protein ===")
    recs = recommend("paneer", 250, 12, db)
    for r in recs:
        print(f"  {r['name']:16} {r['grams']}g -> {r['calories']} cal, {r['protein_g']}g protein")

    print("\n=== reply ===")
    print(build_reply("paneer", 250, 12, recs, "hinglish"))

    print("\n=== chicken, <=300 cal, >=25g protein ===")
    recs2 = recommend("chicken", 300, 25, db)
    print(build_reply("chicken", 300, 25, recs2, "english"))
