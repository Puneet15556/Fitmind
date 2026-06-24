"""
Seed Indian nutrition database — 150+ most-eaten foods for gym bros.
Values per typical serving (not per 100g — gym bros think in "1 roti", "1 bowl").
Sources cross-checked: IFCT 2017, USDA FoodData Central, HealthifyMe.
"""

import csv
from pathlib import Path

# Schema: (name, category, typical_serving, calories, protein_g, carbs_g, fat_g, fiber_g)
# Calories use realistic ranges — gym bros need honest numbers, not fake precision.

FOODS = [
    # ---------- ROTI / BREAD ----------
    ("roti",              "bread",    "1 piece (40g)",   75,   2.5,  15,   1.5, 1.5),
    ("phulka",            "bread",    "1 piece (30g)",   60,   2.0,  12,   0.8, 1.2),
    ("paratha plain",     "bread",    "1 piece (60g)",   170,  4.0,  22,   7.0, 2.0),
    ("paratha aloo",      "bread",    "1 piece (80g)",   210,  4.5,  28,   9.0, 2.5),
    ("paratha butter",    "bread",    "1 piece (60g)",   220,  4.0,  22,   12,  2.0),
    ("naan plain",        "bread",    "1 piece (100g)",  260,  8.0,  45,   5.0, 1.8),
    ("naan butter",       "bread",    "1 piece (100g)",  310,  8.0,  45,   10,  1.8),
    ("garlic naan",       "bread",    "1 piece (100g)",  290,  8.5,  46,   8.0, 2.0),
    ("kulcha",            "bread",    "1 piece (100g)",  270,  7.0,  46,   6.5, 1.5),
    ("bhatura",           "bread",    "1 piece (80g)",   270,  5.5,  35,   12,  1.5),
    ("puri",              "bread",    "1 piece (25g)",   85,   1.5,  10,   4.5, 0.5),
    ("luchi",             "bread",    "1 piece (25g)",   90,   1.5,  10,   5.0, 0.5),
    ("makki ki roti",     "bread",    "1 piece (50g)",   105,  2.5,  18,   3.0, 2.0),
    ("bajra roti",        "bread",    "1 piece (50g)",   110,  3.0,  20,   2.5, 3.5),
    ("jowar roti",        "bread",    "1 piece (50g)",   100,  2.5,  19,   2.0, 3.0),
    ("ragi roti",         "bread",    "1 piece (50g)",   105,  3.0,  20,   2.0, 3.5),
    ("missi roti",        "bread",    "1 piece (60g)",   140,  5.0,  22,   4.0, 3.0),
    ("rumali roti",       "bread",    "1 piece (40g)",   95,   3.0,  18,   1.5, 1.0),

    # ---------- RICE ----------
    ("rice plain",        "rice",     "1 katori (150g)", 200,  4.0,  44,   0.5, 0.5),
    ("rice brown",        "rice",     "1 katori (150g)", 215,  5.0,  45,   1.5, 2.5),
    ("jeera rice",        "rice",     "1 katori (150g)", 245,  4.5,  44,   6.0, 0.8),
    ("ghee rice",         "rice",     "1 katori (150g)", 290,  4.5,  44,   12,  0.8),
    ("biryani veg",       "rice",     "1 plate (300g)",  450,  10,   65,   16,  4.0),
    ("biryani chicken",   "rice",     "1 plate (300g)",  580,  28,   55,   25,  3.5),
    ("biryani mutton",    "rice",     "1 plate (300g)",  650,  30,   55,   32,  3.5),
    ("pulao veg",         "rice",     "1 katori (150g)", 280,  6.0,  45,   8.0, 3.0),
    ("pulao matar",       "rice",     "1 katori (150g)", 270,  7.0,  44,   7.5, 3.5),
    ("lemon rice",        "rice",     "1 katori (150g)", 240,  5.0,  44,   5.5, 1.5),
    ("curd rice",         "rice",     "1 katori (200g)", 230,  7.0,  40,   4.0, 1.0),
    ("khichdi",           "rice",     "1 katori (200g)", 240,  9.0,  42,   3.5, 4.0),

    # ---------- DAL / LEGUMES ----------
    ("dal tadka",         "dal",      "1 katori (150g)", 150,  9.0,  20,   4.0, 6.0),
    ("dal fry",           "dal",      "1 katori (150g)", 165,  9.0,  20,   5.5, 6.0),
    ("dal makhani",       "dal",      "1 katori (150g)", 280,  10,   22,   16,  7.0),
    ("dal chana",         "dal",      "1 katori (150g)", 180,  10,   24,   4.5, 7.5),
    ("dal moong",         "dal",      "1 katori (150g)", 140,  10,   18,   2.5, 5.5),
    ("dal masoor",        "dal",      "1 katori (150g)", 150,  10,   20,   3.0, 6.0),
    ("dal urad",          "dal",      "1 katori (150g)", 170,  11,   22,   4.0, 6.5),
    ("rajma",             "dal",      "1 katori (150g)", 200,  11,   30,   4.0, 8.0),
    ("chole",             "dal",      "1 katori (150g)", 230,  10,   30,   8.0, 8.5),
    ("kala chana",        "dal",      "1 katori (150g)", 210,  11,   30,   5.5, 9.0),
    ("sambar",            "dal",      "1 katori (200g)", 140,  6.0,  20,   4.0, 5.0),
    ("rasam",             "dal",      "1 katori (200g)", 70,   3.0,  10,   2.0, 1.5),

    # ---------- SABZI / VEG CURRY ----------
    ("aloo gobi",         "sabzi",    "1 katori (150g)", 160,  4.0,  20,   7.5, 4.5),
    ("aloo matar",        "sabzi",    "1 katori (150g)", 180,  5.0,  25,   7.0, 4.5),
    ("aloo bhindi",       "sabzi",    "1 katori (150g)", 150,  3.5,  20,   6.5, 5.0),
    ("bhindi masala",     "sabzi",    "1 katori (150g)", 140,  3.0,  16,   8.0, 5.5),
    ("baingan bharta",    "sabzi",    "1 katori (150g)", 155,  3.0,  16,   9.0, 5.0),
    ("palak paneer",      "sabzi",    "1 katori (150g)", 280,  14,   12,   20,  4.0),
    ("paneer butter",     "sabzi",    "1 katori (150g)", 380,  16,   12,   30,  2.5),
    ("paneer tikka",      "sabzi",    "1 plate (150g)",  320,  20,   8.0,  24,  2.0),
    ("matar paneer",      "sabzi",    "1 katori (150g)", 290,  14,   18,   18,  4.5),
    ("kadhai paneer",     "sabzi",    "1 katori (150g)", 320,  15,   14,   23,  3.5),
    ("shahi paneer",      "sabzi",    "1 katori (150g)", 360,  15,   16,   27,  3.0),
    ("malai kofta",       "sabzi",    "1 katori (150g)", 380,  10,   22,   28,  3.0),
    ("mix veg",           "sabzi",    "1 katori (150g)", 150,  4.0,  18,   7.0, 5.0),
    ("kadhi pakora",      "sabzi",    "1 katori (150g)", 220,  7.0,  20,   12,  2.0),
    ("dum aloo",          "sabzi",    "1 katori (150g)", 230,  4.0,  28,   12,  3.5),
    ("aloo jeera",        "sabzi",    "1 katori (150g)", 170,  3.0,  24,   7.5, 3.0),
    ("gobi manchurian",   "sabzi",    "1 plate (200g)",  340,  7.0,  36,   18,  5.0),
    ("chilli paneer",     "sabzi",    "1 plate (200g)",  420,  20,   22,   28,  3.0),

    # ---------- NON-VEG ----------
    ("chicken curry",     "nonveg",   "1 katori (150g)", 280,  25,   8.0,  17,  1.5),
    ("butter chicken",    "nonveg",   "1 katori (150g)", 380,  24,   10,   28,  2.0),
    ("chicken tikka",     "nonveg",   "1 plate (150g)",  290,  32,   6.0,  16,  1.0),
    ("chicken biryani",   "nonveg",   "1 plate (300g)",  580,  28,   55,   25,  3.5),
    ("tandoori chicken",  "nonveg",   "1 plate (200g)",  330,  40,   4.0,  17,  0.5),
    ("chicken 65",        "nonveg",   "1 plate (200g)",  410,  30,   18,   24,  2.0),
    ("mutton curry",      "nonveg",   "1 katori (150g)", 380,  26,   8.0,  27,  1.5),
    ("mutton biryani",    "nonveg",   "1 plate (300g)",  650,  30,   55,   32,  3.5),
    ("fish curry",        "nonveg",   "1 katori (150g)", 240,  24,   8.0,  12,  1.5),
    ("fish fry",          "nonveg",   "1 plate (150g)",  290,  28,   10,   16,  0.8),
    ("egg curry",         "nonveg",   "1 katori (150g)", 220,  14,   8.0,  15,  1.5),
    ("egg bhurji",        "nonveg",   "1 plate (100g)",  200,  13,   4.0,  15,  0.8),
    ("omelette",          "nonveg",   "2 eggs (100g)",   180,  12,   2.0,  14,  0.3),
    ("boiled egg",        "nonveg",   "1 egg (50g)",     75,   6.5,  0.5,  5.0, 0.0),

    # ---------- BREAKFAST ----------
    ("poha",              "breakfast","1 plate (200g)",  270,  6.0,  45,   7.0, 3.5),
    ("upma",              "breakfast","1 plate (200g)",  240,  7.0,  40,   6.5, 3.0),
    ("idli",              "breakfast","2 pieces (100g)", 150,  4.0,  32,   0.5, 1.5),
    ("dosa plain",        "breakfast","1 piece (100g)",  165,  4.0,  28,   4.5, 1.5),
    ("dosa masala",       "breakfast","1 piece (200g)",  280,  6.0,  44,   9.0, 3.5),
    ("dosa onion",        "breakfast","1 piece (150g)",  220,  5.0,  34,   7.0, 2.5),
    ("uttapam",           "breakfast","1 piece (150g)",  240,  6.0,  38,   6.5, 2.5),
    ("medu vada",         "breakfast","2 pieces (80g)",  220,  6.0,  20,   12,  2.5),
    ("sabudana khichdi",  "breakfast","1 plate (200g)",  320,  4.0,  50,   12,  2.0),
    ("paratha curd",      "breakfast","1+bowl",          280,  8.0,  30,   12,  2.5),
    ("besan chilla",      "breakfast","1 piece (80g)",   145,  7.0,  14,   6.5, 3.0),
    ("oats",              "breakfast","1 bowl (40g dry)",160,  6.0,  28,   3.0, 4.5),
    ("daliya",            "breakfast","1 bowl (200g)",   220,  7.0,  42,   3.0, 5.5),
    ("cornflakes milk",   "breakfast","1 bowl",          230,  8.0,  40,   4.5, 1.5),
    ("muesli milk",       "breakfast","1 bowl",          290,  10,   45,   7.0, 4.0),

    # ---------- SNACKS / STREET FOOD ----------
    ("samosa",            "snack",    "1 piece (60g)",   200,  4.0,  22,   11,  1.5),
    ("kachori",           "snack",    "1 piece (60g)",   220,  4.0,  24,   12,  1.5),
    ("pakora",            "snack",    "1 plate (100g)",  280,  6.0,  22,   18,  2.5),
    ("bhel puri",         "snack",    "1 plate (150g)",  290,  6.0,  44,   10,  4.0),
    ("pani puri",         "snack",    "6 pieces (90g)",  170,  4.0,  28,   5.0, 2.0),
    ("dahi puri",         "snack",    "6 pieces (120g)", 240,  6.0,  32,   10,  2.5),
    ("sev puri",          "snack",    "6 pieces (120g)", 270,  6.0,  34,   12,  2.5),
    ("vada pav",          "snack",    "1 piece (120g)",  300,  7.0,  38,   13,  3.0),
    ("pav bhaji",         "snack",    "1 plate (200g)",  450,  9.0,  56,   20,  6.0),
    ("misal pav",         "snack",    "1 plate (250g)",  420,  14,   54,   16,  9.0),
    ("dabeli",            "snack",    "1 piece (100g)",  260,  6.0,  35,   11,  3.0),
    ("kathi roll veg",    "snack",    "1 piece (150g)",  340,  8.0,  40,   16,  3.0),
    ("kathi roll paneer", "snack",    "1 piece (150g)",  410,  16,   38,   22,  3.0),
    ("kathi roll chicken","snack",    "1 piece (150g)",  430,  22,   38,   22,  2.5),
    ("frankie",           "snack",    "1 piece (150g)",  380,  10,   40,   20,  2.5),
    ("momos veg",         "snack",    "6 pieces (180g)", 280,  8.0,  50,   5.0, 3.0),
    ("momos chicken",     "snack",    "6 pieces (180g)", 340,  18,   46,   8.0, 2.5),
    ("momos fried",       "snack",    "6 pieces (180g)", 420,  10,   50,   20,  3.0),
    ("aloo tikki",        "snack",    "2 pieces (100g)", 230,  4.0,  28,   12,  3.0),
    ("chole bhature",     "snack",    "1 plate",         650,  16,   75,   30,  10),
    ("paneer pakora",     "snack",    "1 plate (100g)",  340,  14,   16,   24,  1.5),
    ("french fries",      "snack",    "1 medium (120g)", 365,  4.0,  48,   17,  4.0),
    ("burger veg",        "snack",    "1 piece",         360,  10,   48,   14,  3.0),
    ("burger chicken",    "snack",    "1 piece",         440,  22,   44,   20,  2.5),
    ("pizza margherita",  "snack",    "1 slice (100g)",  240,  10,   30,   8.0, 2.0),
    ("pizza veg",         "snack",    "1 slice (110g)",  260,  11,   30,   10,  2.5),
    ("pizza chicken",     "snack",    "1 slice (120g)",  290,  14,   30,   12,  2.0),
    ("sandwich veg",      "snack",    "1 piece (120g)",  240,  7.0,  36,   8.0, 4.0),
    ("sandwich grilled",  "snack",    "1 piece (150g)",  340,  11,   38,   16,  4.0),
    ("maggi",             "snack",    "1 pack (70g dry)",310,  7.0,  42,   12,  2.0),
    ("pasta red sauce",   "snack",    "1 plate (200g)",  380,  11,   58,   11,  4.0),
    ("pasta white sauce", "snack",    "1 plate (200g)",  470,  14,   52,   22,  3.0),

    # ---------- DAIRY ----------
    ("milk full fat",     "dairy",    "1 glass (250ml)", 160,  8.0,  12,   8.5, 0),
    ("milk toned",        "dairy",    "1 glass (250ml)", 120,  8.0,  12,   4.0, 0),
    ("milk skimmed",      "dairy",    "1 glass (250ml)", 85,   8.5,  13,   0.5, 0),
    ("curd",              "dairy",    "1 katori (150g)", 100,  5.5,  6.5,  5.5, 0),
    ("dahi low fat",      "dairy",    "1 katori (150g)", 70,   6.0,  7.0,  1.5, 0),
    ("paneer",            "dairy",    "100g",            290,  18,   3.5,  22,  0),
    ("cheese slice",      "dairy",    "1 slice (20g)",   70,   4.0,  0.5,  5.5, 0),
    ("butter",            "dairy",    "1 tbsp (15g)",    110,  0.1,  0.0,  12,  0),
    ("ghee",              "dairy",    "1 tsp (5g)",      45,   0,    0,    5.0, 0),
    ("lassi sweet",       "dairy",    "1 glass (300ml)", 220,  6.0,  30,   8.0, 0),
    ("lassi salted",      "dairy",    "1 glass (300ml)", 110,  6.0,  9.0,  5.5, 0),
    ("buttermilk",        "dairy",    "1 glass (250ml)", 60,   4.0,  6.0,  2.0, 0),

    # ---------- SWEETS ----------
    ("gulab jamun",       "sweet",    "2 pieces (60g)",  280,  4.0,  40,   12,  0.5),
    ("rasgulla",          "sweet",    "2 pieces (80g)",  210,  6.0,  38,   4.0, 0),
    ("jalebi",            "sweet",    "100g",            380,  3.0,  60,   15,  0.3),
    ("kheer",             "sweet",    "1 katori (150g)", 220,  6.0,  32,   8.0, 0.5),
    ("halwa gajar",       "sweet",    "1 katori (150g)", 320,  5.0,  40,   16,  3.0),
    ("halwa suji",        "sweet",    "1 katori (150g)", 340,  5.0,  48,   14,  1.5),
    ("ladoo besan",       "sweet",    "1 piece (40g)",   180,  3.5,  22,   9.0, 1.0),
    ("ladoo motichoor",   "sweet",    "1 piece (40g)",   190,  3.0,  26,   9.0, 0.5),
    ("barfi",             "sweet",    "1 piece (40g)",   170,  3.5,  20,   9.0, 0.3),
    ("kaju katli",        "sweet",    "2 pieces (30g)",  150,  3.5,  16,   8.0, 0.5),
    ("rasmalai",          "sweet",    "2 pieces (100g)", 280,  8.0,  32,   13,  0),
    ("ice cream vanilla", "sweet",    "1 scoop (75g)",   150,  3.0,  18,   8.0, 0),
    ("chocolate",         "sweet",    "1 bar (40g)",     220,  3.0,  24,   13,  1.5),

    # ---------- BEVERAGES ----------
    ("tea milk",          "drink",    "1 cup (150ml)",   60,   2.0,  8.0,  2.0, 0),
    ("tea black",         "drink",    "1 cup (150ml)",   25,   0,    6.0,  0,   0),
    ("coffee milk",       "drink",    "1 cup (150ml)",   80,   3.0,  10,   3.0, 0),
    ("filter coffee",     "drink",    "1 cup (150ml)",   90,   3.5,  11,   3.5, 0),
    ("coke",              "drink",    "1 can (330ml)",   140,  0,    36,   0,   0),
    ("pepsi",             "drink",    "1 can (330ml)",   140,  0,    36,   0,   0),
    ("juice orange",      "drink",    "1 glass (250ml)", 110,  1.5,  26,   0.3, 0.5),
    ("coconut water",     "drink",    "1 glass (250ml)", 45,   1.5,  9.0,  0.5, 0.5),
    ("nimbu pani sweet",  "drink",    "1 glass (250ml)", 90,   0.3,  22,   0.1, 0),
    ("protein shake",     "drink",    "1 scoop+milk",    280,  30,   18,   8.0, 0.5),

    # ---------- FRUITS ----------
    ("apple",             "fruit",    "1 medium (180g)", 95,   0.5,  25,   0.3, 4.5),
    ("banana",            "fruit",    "1 medium (120g)", 105,  1.3,  27,   0.4, 3.0),
    ("orange",            "fruit",    "1 medium (130g)", 60,   1.2,  15,   0.2, 3.0),
    ("mango",             "fruit",    "1 medium (200g)", 200,  2.8,  50,   1.3, 5.5),
    ("grapes",            "fruit",    "1 cup (150g)",    105,  1.0,  27,   0.3, 1.5),
    ("watermelon",        "fruit",    "1 cup (150g)",    45,   1.0,  11,   0.2, 0.6),
    ("papaya",            "fruit",    "1 cup (150g)",    60,   1.0,  15,   0.4, 2.5),
    ("guava",             "fruit",    "1 medium (120g)", 70,   2.5,  15,   1.0, 5.5),
    ("pomegranate",       "fruit",    "1 cup (175g)",    145,  3.0,  33,   2.0, 7.0),

    # ---------- NUTS / EXTRAS ----------
    ("almonds",           "nuts",     "10 pieces (12g)", 70,   2.5,  2.5,  6.0, 1.5),
    ("cashews",           "nuts",     "10 pieces (15g)", 85,   2.5,  4.5,  7.0, 0.5),
    ("walnuts",           "nuts",     "4 halves (15g)",  100,  2.5,  2.0,  10,  1.0),
    ("peanuts",           "nuts",     "30g",             170,  7.5,  5.0,  14,  2.5),
    ("dates",             "nuts",     "3 pieces (24g)",  70,   0.5,  18,   0.1, 1.8),
]

OUT = Path(__file__).resolve().parent.parent / "data" / "processed" / "nutrition_seed.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["food_name", "category", "typical_serving",
                "calories", "protein_g", "carbs_g", "fat_g", "fiber_g"])
    w.writerows(FOODS)

print(f"Wrote {len(FOODS)} foods to {OUT}")
