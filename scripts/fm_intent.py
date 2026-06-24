"""
Intent router — decides what the user is trying to do.

Hybrid approach (rules + model):
  1. detect_intent_rules()  -> fast keyword match for CLEAR cases (no model call)
  2. if rules are unsure    -> ask the SLM to classify (covers novel phrasings)

Intents:
  log       -> user is logging food they ate         ("2 roti khaya")
  recommend -> user wants a suggestion + constraints  ("250 cal me paneer kaise khau")
  query     -> user asks about today's total/budget   ("aaj kitna khaya")
  help      -> anything else                          ("what do you do")

Precision from rules, coverage from the model.
"""

import re

# --- keyword sets per intent (order of CHECKS matters: specific first) -----
RECOMMEND_TRIGGERS = ["khaau", "khau", "khaun", "kya lu", "kya khau", "suggest",
                      "recommend", "chahiye", "what should i eat", "advise", "batao kya"]
RECOMMEND_CONSTRAINTS = ["cal", "calorie", "protein", "gram", "gm", " g ", "macros"]

QUERY_TRIGGERS = ["kitna khaya", "kitna ho gaya", "kitni calorie", "total kitna",
                  "how much have i", "today total", "aaj kitna", "budget left",
                  "kitna bacha", "mera total"]

LOG_TRIGGERS = ["khaya", "khaye", "khaayi", "khai", "kha li", "kha liye", "kha liya",
                "ate", "had ", "i had", "just had", "liya", "piya", "pi liya", "khilaya"]


def detect_intent_rules(text):
    """Return an intent string if confident, else None (let the model decide)."""
    t = " " + (text or "").lower().strip() + " "

    has_log = any(w in t for w in LOG_TRIGGERS)
    has_cal = any(w in t for w in ["cal", "calorie", "kcal"])
    has_protein = "protein" in t

    # 1. RECOMMEND — either an explicit "what to eat" trigger + a constraint,
    #    OR both a calorie and protein constraint with no "I ate" verb.
    if (any(w in t for w in RECOMMEND_TRIGGERS) and (has_cal or has_protein)) or \
       (has_cal and has_protein and not has_log):
        return "recommend"

    # 2. QUERY — asking about today's running total/budget
    if any(w in t for w in QUERY_TRIGGERS):
        return "query"

    # 3. LOG — past-tense eating
    if has_log:
        return "log"

    # 4. unsure
    return None


def detect_intent(text, model=None):
    """Rules first; SLM fallback when rules are unsure.
    Returns (intent, source) where source is 'rules' | 'model' | 'default'."""
    intent = detect_intent_rules(text)
    if intent is not None:
        return intent, "rules"
    if model is not None:
        try:
            intent = model.classify_intent(text)
            if intent in ("log", "recommend", "query", "help"):
                return intent, "model"
        except Exception:
            pass
    return "help", "default"   # safe fallback


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    p = f = 0
    def chk(text, expected):
        global p, f
        got = detect_intent_rules(text)
        ok = got == expected
        p += ok; f += (not ok)
        print(f"  {'PASS' if ok else 'FAIL'}  [{got}] expected [{expected}]  <- {text}")

    print("RULE-BASED intent tests:")
    chk("abhi maine 2 roti aur dal khaya", "log")
    chk("I had grilled chicken", "log")
    chk("subah 3 paratha le liya", "log")
    chk("250 cal me paneer kaise khau", "recommend")
    chk("suggest something with 20g protein under 300 cal", "recommend")
    chk("aaj kitna khaya hai", "query")
    chk("how much have i eaten today", "query")
    chk("mera budget left kitna hai", "query")
    chk("what do you do", None)          # unsure -> model/help
    chk("hello bhai", None)              # unsure

    print(f"\nRESULTS: {p} passed, {f} failed")
    sys.exit(0 if f == 0 else 1)
