"""
Extension to seed_nutrition.py — adds ~160 more foods covering:
- Regional Indian (Bengali, South, Gujarati, Maharashtrian, Punjabi)
- Gym/diet foods (chicken breast, salads, sprouts)
- Chinese-Indian
- Junk/packaged foods (chips, biscuits)
- Restaurant items
- Vegetables (raw quantities)
- More breakfast options
Combines with nutrition_seed.csv to produce nutrition.csv (final).
"""

import csv
from pathlib import Path

EXTRA_FOODS = [
    # ---------- SOUTH INDIAN EXTRA ----------
    ("rava dosa",             "breakfast", "1 piece (120g)",  220,  4.5,  32,   8.0, 1.5),
    ("set dosa",              "breakfast", "2 pieces (120g)", 180,  4.5,  30,   5.5, 1.5),
    ("paper dosa",            "breakfast", "1 piece (80g)",   140,  3.5,  24,   3.5, 1.0),
    ("mysore dosa",           "breakfast", "1 piece (150g)",  240,  5.5,  36,   8.5, 2.5),
    ("ghee roast dosa",       "breakfast", "1 piece (120g)",  280,  4.0,  30,   16,  1.5),
    ("appam",                 "breakfast", "1 piece (60g)",   120,  2.0,  22,   3.0, 0.5),
    ("idiyappam",             "breakfast", "1 plate (150g)",  220,  4.0,  46,   1.5, 1.5),
    ("puttu",                 "breakfast", "1 piece (100g)",  180,  3.5,  38,   1.5, 2.0),
    ("vada sambar",           "breakfast", "2 vada + bowl",   330,  10,   40,   14,  4.5),
    ("rasam rice",            "rice",      "1 plate (250g)",  270,  6.0,  50,   3.0, 2.0),
    ("sambar rice",           "rice",      "1 plate (250g)",  310,  9.0,  54,   5.0, 4.0),
    ("curd rice south",       "rice",      "1 plate (250g)",  280,  9.0,  46,   5.5, 1.5),
    ("bisi bele bath",        "rice",      "1 plate (200g)",  330,  10,   52,   8.5, 4.5),
    ("pongal sweet",          "breakfast", "1 katori (150g)", 290,  6.0,  46,   9.0, 2.0),
    ("pongal khara",          "breakfast", "1 katori (150g)", 250,  7.0,  40,   7.0, 2.5),
    ("coconut chutney",       "sabzi",     "2 tbsp (30g)",    80,   1.5,  3.0,  7.0, 1.5),
    ("tomato chutney",        "sabzi",     "2 tbsp (30g)",    45,   1.0,  6.0,  2.0, 1.0),

    # ---------- BENGALI ----------
    ("alur dom bengali",      "sabzi",     "1 katori (150g)", 250,  4.5,  30,   13,  3.5),
    ("shorshe ilish",         "nonveg",    "1 piece (100g)",  280,  20,   3.0,  22,  0.5),
    ("kosha mangsho",         "nonveg",    "1 katori (150g)", 420,  28,   8.0,  30,  1.5),
    ("chingri malai curry",   "nonveg",    "1 katori (150g)", 320,  22,   10,   22,  1.0),
    ("mishti doi",            "sweet",     "1 katori (100g)", 180,  4.0,  28,   5.5, 0),
    ("sandesh",               "sweet",     "1 piece (40g)",   120,  4.0,  18,   4.0, 0),
    ("rosogolla",             "sweet",     "2 pieces (80g)",  210,  6.0,  38,   4.0, 0),
    ("kathi roll egg",        "snack",     "1 piece (150g)",  390,  16,   38,   20,  2.5),

    # ---------- GUJARATI ----------
    ("dhokla",                "snack",     "100g",            160,  6.0,  28,   3.0, 2.0),
    ("khaman",                "snack",     "100g",            155,  7.0,  24,   4.0, 2.5),
    ("thepla",                "bread",     "1 piece (40g)",   110,  3.0,  18,   3.5, 2.0),
    ("khandvi",               "snack",     "100g",            150,  5.0,  20,   5.5, 1.5),
    ("undhiyu",               "sabzi",     "1 katori (150g)", 240,  7.0,  28,   12,  6.0),
    ("fafda",                 "snack",     "50g",             220,  6.0,  22,   12,  2.0),
    ("gathiya",               "snack",     "50g",             260,  6.5,  24,   16,  1.5),
    ("handvo",                "snack",     "100g",            220,  6.0,  32,   8.0, 3.0),
    ("muthia",                "snack",     "100g",            190,  5.0,  30,   6.0, 3.5),
    ("shrikhand",             "sweet",     "1 katori (100g)", 270,  6.0,  36,   11,  0),

    # ---------- MAHARASHTRIAN ----------
    ("puran poli",            "sweet",     "1 piece (80g)",   280,  6.0,  44,   9.0, 3.0),
    ("modak",                 "sweet",     "2 pieces (60g)",  220,  3.0,  32,   9.0, 1.5),
    ("sabudana vada",         "snack",     "2 pieces (80g)",  230,  3.5,  28,   12,  1.5),
    ("kothimbir vadi",        "snack",     "100g",            210,  6.0,  26,   9.0, 3.5),
    ("thalipeeth",            "bread",     "1 piece (80g)",   180,  5.5,  28,   5.5, 4.0),
    ("misal",                 "snack",     "1 plate (200g)",  340,  13,   42,   13,  8.0),

    # ---------- PUNJABI EXTRA ----------
    ("amritsari kulcha",      "bread",     "1 piece (120g)",  340,  8.0,  52,   10,  2.5),
    ("sarson ka saag",        "sabzi",     "1 katori (150g)", 180,  6.0,  16,   10,  6.0),
    ("makke ki roti saag",    "bread",     "combo plate",     310,  9.0,  38,   13,  8.0),
    ("lassi mango",           "drink",     "1 glass (300ml)", 260,  6.0,  40,   8.0, 1.0),
    ("paneer bhurji",         "sabzi",     "1 katori (150g)", 290,  16,   8.0,  22,  2.0),
    ("aloo paratha curd",     "breakfast", "1+bowl",          320,  8.0,  36,   15,  3.0),
    ("kadhi punjabi",         "sabzi",     "1 katori (200g)", 200,  7.0,  20,   10,  1.5),

    # ---------- CHINESE-INDIAN ----------
    ("hakka noodles veg",     "snack",     "1 plate (250g)",  380,  9.0,  56,   12,  4.0),
    ("hakka noodles chicken", "snack",     "1 plate (250g)",  460,  20,   54,   16,  3.5),
    ("schezwan noodles",      "snack",     "1 plate (250g)",  430,  10,   58,   16,  4.5),
    ("fried rice veg",        "rice",      "1 plate (250g)",  400,  9.0,  60,   12,  3.5),
    ("fried rice chicken",    "rice",      "1 plate (250g)",  480,  22,   58,   16,  3.0),
    ("manchurian veg",        "snack",     "1 plate (200g)",  340,  8.0,  40,   16,  4.0),
    ("manchurian chicken",    "snack",     "1 plate (200g)",  420,  24,   30,   22,  2.5),
    ("chowmein",              "snack",     "1 plate (250g)",  410,  10,   58,   14,  4.0),
    ("spring roll veg",       "snack",     "2 pieces (100g)", 240,  4.0,  28,   12,  3.0),
    ("dimsum veg",            "snack",     "6 pieces (180g)", 270,  7.0,  48,   5.0, 3.0),
    ("honey chilli potato",   "snack",     "1 plate (200g)",  410,  5.0,  56,   18,  4.0),
    ("chilli chicken",        "snack",     "1 plate (200g)",  450,  28,   24,   25,  2.0),
    ("chilli garlic noodles", "snack",     "1 plate (250g)",  420,  10,   58,   15,  4.0),

    # ---------- GYM / DIET FOODS ----------
    ("chicken breast grilled","nonveg",    "100g",            165,  31,   0,    3.6, 0),
    ("chicken breast boiled", "nonveg",    "100g",            150,  30,   0,    3.0, 0),
    ("egg white",             "nonveg",    "3 whites (100g)", 50,   11,   0.7,  0.2, 0),
    ("tuna canned",           "nonveg",    "100g",            115,  26,   0,    1.0, 0),
    ("salmon grilled",        "nonveg",    "100g",            210,  22,   0,    13,  0),
    ("fish grilled",          "nonveg",    "100g",            140,  22,   0,    6.0, 0),
    ("paneer grilled",        "sabzi",     "100g",            280,  19,   3.0,  21,  0),
    ("tofu",                  "sabzi",     "100g",            145,  17,   3.0,  8.0, 2.0),
    ("sprouts moong",         "snack",     "1 katori (100g)", 100,  7.0,  18,   0.7, 4.5),
    ("sprouts chana",         "snack",     "1 katori (100g)", 120,  8.0,  20,   1.5, 5.0),
    ("salad green",           "salad",     "1 plate (150g)",  60,   3.0,  10,   0.8, 4.0),
    ("salad sprouts",         "salad",     "1 plate (150g)",  140,  9.0,  22,   1.5, 6.0),
    ("salad caesar",          "salad",     "1 plate (200g)",  290,  10,   12,   22,  3.0),
    ("salad chicken",         "salad",     "1 plate (250g)",  320,  28,   12,   18,  4.0),
    ("salad fruit",           "salad",     "1 plate (200g)",  150,  2.0,  36,   0.5, 5.5),
    ("smoothie banana",       "drink",     "1 glass (300ml)", 240,  8.0,  42,   4.5, 3.0),
    ("smoothie protein",      "drink",     "1 glass (300ml)", 320,  32,   30,   8.0, 3.5),
    ("greek yogurt",          "dairy",     "1 katori (170g)", 100,  17,   6.0,  0.7, 0),
    ("peanut butter",         "nuts",      "1 tbsp (16g)",    95,   3.5,  3.5,  8.0, 1.0),
    ("almond butter",         "nuts",      "1 tbsp (16g)",    100,  3.5,  3.0,  9.0, 1.5),
    ("oatmeal milk",          "breakfast", "1 bowl (200g)",   220,  9.0,  32,   6.0, 5.0),
    ("quinoa cooked",         "rice",      "1 katori (150g)", 180,  6.5,  32,   3.0, 4.0),
    ("brown rice",            "rice",      "1 katori (150g)", 215,  5.0,  45,   1.5, 2.5),
    ("multigrain bread",      "bread",     "2 slices (60g)",  160,  6.0,  30,   2.0, 4.0),
    ("brown bread",           "bread",     "2 slices (60g)",  150,  5.0,  28,   1.5, 3.5),
    ("white bread",           "bread",     "2 slices (60g)",  160,  4.5,  30,   2.0, 1.5),

    # ---------- JUNK / PACKAGED ----------
    ("chips potato",          "snack",     "1 packet (52g)",  280,  3.0,  30,   17,  2.5),
    ("kurkure",               "snack",     "1 packet (45g)",  240,  3.5,  26,   13,  1.5),
    ("haldiram bhujia",       "snack",     "30g",             170,  5.0,  14,   11,  1.5),
    ("namkeen mix",           "snack",     "30g",             160,  5.0,  16,   9.0, 1.5),
    ("biscuits parle g",      "snack",     "5 pieces (30g)",  140,  2.0,  22,   4.5, 0.5),
    ("biscuits marie",        "snack",     "5 pieces (30g)",  135,  2.5,  22,   4.0, 0.5),
    ("biscuits oreo",         "snack",     "3 pieces (33g)",  160,  1.5,  24,   7.0, 1.0),
    ("biscuits hide seek",    "snack",     "4 pieces (40g)",  200,  2.5,  26,   9.5, 0.5),
    ("rusk",                  "snack",     "2 pieces (30g)",  120,  3.0,  22,   2.5, 1.0),
    ("khakra",                "snack",     "2 pieces (30g)",  110,  3.5,  20,   2.0, 2.5),
    ("popcorn plain",         "snack",     "1 bowl (30g)",    110,  3.5,  22,   1.5, 4.0),
    ("popcorn butter",        "snack",     "1 bowl (30g)",    170,  3.0,  20,   9.0, 3.5),
    ("nachos",                "snack",     "1 plate (100g)",  490,  6.0,  60,   24,  4.0),
    ("doughnut",              "sweet",     "1 piece (60g)",   250,  4.0,  30,   12,  1.0),
    ("muffin",                "sweet",     "1 piece (100g)",  370,  5.0,  52,   16,  2.0),
    ("pastry",                "sweet",     "1 piece (100g)",  370,  4.0,  44,   20,  1.0),
    ("cookie chocolate",      "sweet",     "1 piece (30g)",   150,  2.0,  20,   7.0, 1.0),

    # ---------- DRINKS EXTRA ----------
    ("masala chai",           "drink",     "1 cup (150ml)",   80,   3.0,  10,   3.0, 0),
    ("green tea",             "drink",     "1 cup (200ml)",   3,    0,    0.5,  0,   0),
    ("lemon tea",             "drink",     "1 cup (200ml)",   30,   0,    7.0,  0,   0),
    ("cold coffee",           "drink",     "1 glass (300ml)", 220,  6.0,  32,   8.0, 0),
    ("hot chocolate",         "drink",     "1 cup (250ml)",   230,  8.0,  30,   9.0, 1.5),
    ("milkshake banana",      "drink",     "1 glass (300ml)", 320,  10,   48,   9.0, 2.5),
    ("milkshake mango",       "drink",     "1 glass (300ml)", 340,  9.0,  56,   8.0, 1.5),
    ("milkshake chocolate",   "drink",     "1 glass (300ml)", 380,  11,   58,   10,  1.5),
    ("juice apple",           "drink",     "1 glass (250ml)", 115,  0.5,  28,   0.3, 0.5),
    ("juice mango",           "drink",     "1 glass (250ml)", 140,  0.8,  34,   0.4, 0.8),
    ("juice pineapple",       "drink",     "1 glass (250ml)", 130,  1.0,  32,   0.3, 0.8),
    ("beer",                  "drink",     "1 bottle (650ml)",290,  3.0,  22,   0,   0),
    ("wine",                  "drink",     "1 glass (150ml)", 125,  0.1,  4.0,  0,   0),
    ("whisky",                "drink",     "30ml peg",        65,   0,    0,    0,   0),
    ("redbull",               "drink",     "1 can (250ml)",   115,  0,    27,   0,   0),
    ("sprite",                "drink",     "1 can (330ml)",   140,  0,    34,   0,   0),
    ("fanta",                 "drink",     "1 can (330ml)",   150,  0,    37,   0,   0),
    ("nimbu pani salted",     "drink",     "1 glass (250ml)", 30,   0.3,  7.0,  0.1, 0),
    ("aam panna",             "drink",     "1 glass (250ml)", 120,  0.5,  30,   0.2, 0.5),

    # ---------- VEGETABLES (RAW/QUANTITY) ----------
    ("potato boiled",         "vegetable", "1 medium (150g)", 130,  3.0,  30,   0.2, 3.0),
    ("sweet potato boiled",   "vegetable", "1 medium (150g)", 130,  2.5,  30,   0.2, 4.5),
    ("paneer raw",            "dairy",     "50g",             145,  9.0,  1.5,  11,  0),
    ("carrot",                "vegetable", "1 medium (60g)",  25,   0.6,  6.0,  0.1, 1.8),
    ("cucumber",              "vegetable", "1 medium (200g)", 30,   1.4,  7.0,  0.2, 1.0),
    ("tomato",                "vegetable", "1 medium (120g)", 22,   1.1,  5.0,  0.2, 1.5),
    ("onion",                 "vegetable", "1 medium (110g)", 45,   1.2,  10,   0.1, 1.8),

    # ---------- FRUITS EXTRA ----------
    ("strawberry",            "fruit",     "1 cup (150g)",    50,   1.0,  12,   0.5, 3.0),
    ("blueberry",             "fruit",     "1 cup (150g)",    85,   1.0,  21,   0.5, 3.5),
    ("pineapple",             "fruit",     "1 cup (165g)",    80,   0.9,  22,   0.2, 2.3),
    ("kiwi",                  "fruit",     "1 medium (75g)",  45,   0.9,  11,   0.4, 2.0),
    ("avocado",               "fruit",     "1/2 medium (75g)",120,  1.5,  6.0,  11,  5.0),
    ("muskmelon",             "fruit",     "1 cup (160g)",    55,   1.4,  13,   0.3, 1.5),
    ("pear",                  "fruit",     "1 medium (180g)", 100,  0.7,  27,   0.3, 5.5),
    ("custard apple",         "fruit",     "1 medium (150g)", 145,  3.0,  35,   1.0, 7.0),
    ("jackfruit",             "fruit",     "1 cup (150g)",    155,  3.0,  40,   1.0, 2.5),
    ("lychee",                "fruit",     "10 pieces (100g)",65,   0.8,  17,   0.4, 1.3),
    ("guava with masala",     "fruit",     "1 plate (200g)",  130,  4.0,  28,   1.5, 9.0),

    # ---------- RESTAURANT / WESTERN ----------
    ("steak grilled",         "nonveg",    "150g",            350,  42,   0,    20,  0),
    ("hot dog",               "snack",     "1 piece (130g)",  330,  11,   28,   20,  1.5),
    ("subway veg",            "snack",     "6 inch",          280,  9.0,  44,   7.0, 5.0),
    ("subway chicken",        "snack",     "6 inch",          340,  22,   42,   8.0, 4.5),
    ("kfc chicken",           "nonveg",    "2 pieces (180g)", 470,  32,   16,   30,  1.0),
    ("donut glazed",          "sweet",     "1 piece (60g)",   240,  3.0,  34,   11,  0.5),
    ("brownie",               "sweet",     "1 piece (80g)",   320,  4.0,  44,   15,  1.5),
    ("waffle",                "breakfast", "1 piece (75g)",   220,  5.0,  25,   11,  1.0),
    ("pancake",               "breakfast", "2 pieces (150g)", 350,  8.0,  44,   16,  1.5),
    ("french toast",          "breakfast", "2 pieces (150g)", 300,  10,   32,   15,  1.5),
    ("club sandwich",         "snack",     "1 piece (200g)",  450,  20,   48,   20,  3.5),
    ("pasta alfredo",         "snack",     "1 plate (250g)",  520,  18,   54,   26,  3.0),
    ("garlic bread",          "snack",     "2 pieces (80g)",  240,  6.0,  30,   11,  1.5),
    ("soup tomato",           "snack",     "1 bowl (250ml)",  110,  3.0,  18,   3.5, 2.0),
    ("soup veg clear",        "snack",     "1 bowl (250ml)",  60,   3.0,  10,   1.0, 2.5),
    ("soup chicken",          "snack",     "1 bowl (250ml)",  140,  10,   12,   5.0, 1.5),
    ("soup hot and sour",     "snack",     "1 bowl (250ml)",  90,   4.0,  14,   2.0, 2.0),
    ("soup sweet corn",       "snack",     "1 bowl (250ml)",  130,  4.0,  22,   2.5, 2.0),

    # ---------- DESSERTS EXTRA ----------
    ("kulfi",                 "sweet",     "1 piece (80g)",   190,  4.0,  20,   10,  0),
    ("falooda",               "sweet",     "1 glass (350g)",  330,  8.0,  52,   10,  1.5),
    ("phirni",                "sweet",     "1 katori (100g)", 200,  5.0,  30,   7.0, 0.5),
    ("malpua",                "sweet",     "1 piece (50g)",   220,  3.5,  30,   10,  0.5),
    ("imarti",                "sweet",     "2 pieces (60g)",  250,  3.0,  36,   11,  0.5),
    ("petha",                 "sweet",     "100g",            240,  0.5,  60,   0.2, 0.8),
    ("soan papdi",            "sweet",     "100g",            500,  6.0,  64,   24,  1.5),
    ("ghevar",                "sweet",     "1 piece (60g)",   270,  3.5,  34,   13,  0.5),

    # ---------- INDIAN SNACKS EXTRA ----------
    ("chaat papri",           "snack",     "1 plate (150g)",  310,  7.0,  44,   12,  4.0),
    ("aloo chaat",            "snack",     "1 plate (200g)",  260,  5.0,  40,   9.0, 4.5),
    ("ragda pattice",         "snack",     "1 plate (250g)",  370,  10,   54,   12,  6.0),
    ("aloo tikki chaat",      "snack",     "1 plate (200g)",  350,  7.0,  46,   15,  4.0),
    ("chila moong dal",       "breakfast", "1 piece (80g)",   140,  8.0,  16,   4.5, 3.5),
    ("dal vada",              "snack",     "2 pieces (80g)",  220,  8.0,  22,   11,  3.0),
    ("masala dosa",           "breakfast", "1 piece (220g)",  300,  6.5,  46,   10,  4.0),
    ("egg dosa",              "breakfast", "1 piece (180g)",  280,  10,   34,   11,  2.0),
    ("paneer dosa",           "breakfast", "1 piece (200g)",  340,  12,   40,   14,  2.5),
    ("pesarattu",             "breakfast", "1 piece (100g)",  180,  9.0,  26,   4.5, 4.5),
    ("akki roti",             "bread",     "1 piece (60g)",   140,  3.0,  26,   3.0, 1.5),
]

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "processed" / "nutrition_seed.csv"
OUT = Path(__file__).resolve().parent.parent / "data" / "processed" / "nutrition.csv"

# Read existing seed
existing = []
with SEED_CSV.open(encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    existing = list(reader)

# Merge
existing_names = {row[0] for row in existing}
new_rows = [list(map(str, row)) for row in EXTRA_FOODS if row[0] not in existing_names]
all_rows = existing + new_rows
all_rows.sort(key=lambda r: (r[1], r[0]))   # sort by category, then name

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(all_rows)

print(f"Seed had {len(existing)} foods")
print(f"Added {len(new_rows)} new foods")
print(f"Final nutrition.csv: {len(all_rows)} foods at {OUT}")

# Category breakdown
from collections import Counter
cats = Counter(r[1] for r in all_rows)
print("\nCategory breakdown:")
for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {cat:12s}: {n}")
