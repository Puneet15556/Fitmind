"""
Calorie budget calculator — deterministic, no model.

Computes a personalized daily calorie target from the user's stats using:
  1. BMR  (Basal Metabolic Rate)  -- Mifflin-St Jeor equation
  2. TDEE (Total Daily Energy)     -- BMR x activity factor
  3. Goal adjustment               -- deficit/surplus for lose/gain

Same "tell, don't guess" principle as the hybrid: exact math, not the model.

  calc_budget(age=25, weight_kg=75, height_cm=175, gender="male",
              activity="moderate", goal="lose") -> dict
"""

# activity multipliers (how much you move beyond resting)
ACTIVITY = {
    "sedentary": 1.2,    # desk job, no exercise
    "light":     1.375,  # 1-3 gym days
    "moderate":  1.55,   # 3-5 gym days
    "active":    1.725,  # 6-7 gym days
    "athlete":   1.9,    # 2x/day, physical job
}

# goal -> daily calorie delta
GOAL_DELTA = {
    "lose":     -500,   # ~0.5 kg/week deficit
    "lose_slow": -250,
    "maintain":  0,
    "gain_slow": 250,
    "gain":      500,   # lean bulk surplus
}


def bmr_mifflin(age, weight_kg, height_cm, gender):
    """Basal Metabolic Rate — calories burned at complete rest."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender.lower().startswith("m") else base - 161


def calc_budget(age, weight_kg, height_cm, gender="male",
                activity="moderate", goal="maintain"):
    """Return a dict with bmr, tdee, and the goal-adjusted daily budget."""
    bmr = bmr_mifflin(age, weight_kg, height_cm, gender)
    factor = ACTIVITY.get(activity, 1.55)
    tdee = bmr * factor
    delta = GOAL_DELTA.get(goal, 0)
    budget = tdee + delta

    # safety floor (never recommend a dangerously low target)
    floor = 1500 if gender.lower().startswith("m") else 1200
    budget = max(floor, budget)

    # also suggest a protein target: ~1.8 g per kg for gym-goers
    protein_target = round(1.8 * weight_kg)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "daily_budget": round(budget),
        "protein_target_g": protein_target,
        "goal": goal,
        "activity": activity,
    }


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    # ---- tests ----
    p, f = 0, 0
    def chk(name, cond, got=""):
        global p, f
        if cond: p += 1; print(f"  PASS {name}")
        else: f += 1; print(f"  FAIL {name} {got}")

    # known reference: male 25y 75kg 175cm
    # BMR = 10*75 + 6.25*175 - 5*25 + 5 = 750 + 1093.75 - 125 + 5 = 1723.75
    b = bmr_mifflin(25, 75, 175, "male")
    chk("BMR male formula", abs(b - 1723.75) < 0.1, f"got {b}")

    # female -161 instead of +5
    bf = bmr_mifflin(25, 60, 165, "female")
    # 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
    chk("BMR female formula", abs(bf - 1345.25) < 0.1, f"got {bf}")

    # full budget, moderate, lose
    r = calc_budget(25, 75, 175, "male", "moderate", "lose")
    # tdee = 1723.75*1.55 = 2671.8; lose -500 = 2171.8 -> 2172
    chk("budget lose ~2172", abs(r["daily_budget"] - 2172) <= 1, f"got {r['daily_budget']}")
    chk("protein target 135g", r["protein_target_g"] == 135, f"got {r['protein_target_g']}")

    # gain adds surplus
    rg = calc_budget(25, 75, 175, "male", "moderate", "gain")
    chk("gain > lose", rg["daily_budget"] > r["daily_budget"])

    # safety floor
    rl = calc_budget(30, 45, 150, "female", "sedentary", "lose")
    chk("never below floor 1200", rl["daily_budget"] >= 1200, f"got {rl['daily_budget']}")

    print(f"\n--- Example: 25y/75kg/175cm male, moderate, lose ---")
    for k, v in calc_budget(25, 75, 175, "male", "moderate", "lose").items():
        print(f"  {k}: {v}")

    print(f"\nRESULTS: {p} passed, {f} failed")
    sys.exit(0 if f == 0 else 1)
