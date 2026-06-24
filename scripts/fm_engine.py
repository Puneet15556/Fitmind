"""
FitMindEngine — the orchestrator that ties everything together.

Flow of engine.process(user_input, user_id):
  1. memory.get_today    -> context (prior meals, running total, budget)
  2. build prompt        -> system + context + user input
  3. model.generate      -> raw text (GGUF or mock)
  4. parse_model_output  -> dict (strips <think>, extracts JSON)
  5. hybrid.process      -> exact CSV numbers + language verify/translate
  6. memory.save_meal    -> persist for the running total
  7. return corrected result

Create once (loads model), call process() many times:
  engine = FitMindEngine(model_path="fitmind-Q4_K_M.gguf")
  engine.process("3 roti aur rajma khaya", user_id=1)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from fm_model import FitMindModel, parse_model_output
from fm_memory import MealMemory
from hybrid import HybridProcessor, detect_language
from fm_intent import detect_intent
import fm_recommend

SYSTEM_PROMPT = (
    "You are FitMind, an offline calorie tracker for Indian gym users. "
    "The user logs food in English, Hindi, or Hinglish. Extract the food items, "
    "estimate calories as a [min, max] range, sum the macros, add this meal to the "
    "running daily total from the context, and compute the remaining budget. "
    "Reply briefly in the SAME language as the user. Always answer with a single JSON object."
)


class FitMindEngine:
    def __init__(self, model_path=None, mock=False, backend="ollama",
                 csv_path=None, db_path=None, default_budget=2000):
        # load each piece ONCE (this is why we use a class)
        self.model = FitMindModel(model_path=model_path, mock=mock, backend=backend)
        self.hybrid = HybridProcessor(csv_path) if csv_path else HybridProcessor()
        self.memory = MealMemory(db_path=db_path, default_budget=default_budget) \
            if db_path else MealMemory(default_budget=default_budget)
        # vocab of words that appear in food names (for the recommender's parser)
        self.food_vocab = set()
        for name in self.hybrid.db.by_name:
            self.food_vocab.update(name.split())

    def _build_user_msg(self, context, user_input):
        budget = context.get("budget", 2000)
        total = context.get("total_cal_so_far", 0)
        meals = context.get("today_meals", [])
        lines = [f"Daily budget: {budget} cal"]
        if meals:
            eaten = "; ".join(
                f"{m['meal']} ({m['cal'][0]}-{m['cal'][1]} cal)" for m in meals)
            lines.append(f"Eaten today: {eaten}")
        else:
            lines.append("Eaten today: nothing yet")
        lines.append(f"Total so far: {total} cal")
        lang = detect_language(user_input)
        lines.append("")
        lines.append(f"User ({lang}): {user_input}")
        return "\n".join(lines)

    def process(self, user_input, user_id=1):
        """Route the input by intent, then call the matching handler."""
        # STEP 0 — intent routing (rules first, SLM fallback)
        intent, source = detect_intent(user_input, model=self.model)
        context = self.memory.get_today(user_id)

        if intent == "log":
            result = self._handle_log(user_input, user_id, context)
        elif intent == "query":
            result = self._handle_query(user_input, context)
        elif intent == "recommend":
            result = self._handle_recommend(user_input, context)
        else:  # help
            result = self._handle_help(user_input)

        result["intent"] = intent
        result["intent_source"] = source       # 'rules' | 'model' (handy for demo)
        return result

    # ---- handlers ---------------------------------------------------
    def _handle_log(self, user_input, user_id, context):
        """The calorie pipeline: model extract -> hybrid fix -> save.
        Safety net: if NO known food was found (e.g. a greeting that got
        misrouted to 'log'), fall back to the clarification handler instead
        of returning an empty/garbage meal."""
        user_msg = self._build_user_msg(context, user_input)
        raw = self.model.generate(SYSTEM_PROMPT, user_msg)
        parsed = parse_model_output(raw)
        if parsed is None or not parsed.get("items"):
            return self._handle_help(user_input)
        result = self.hybrid.process(parsed, user_input, context)
        if not result.get("_meta", {}).get("matched_items"):
            # model "logged" something but no item is in our DB -> clarify
            return self._handle_help(user_input)
        self.memory.save_meal(user_id, user_input, result)
        return result

    def _handle_query(self, user_input, context):
        """Answer 'how much have I eaten' from memory — no model needed."""
        lang = detect_language(user_input)
        total = context["total_cal_so_far"]
        budget = context.get("budget")
        n = len(context.get("today_meals", []))
        if budget is not None:
            left = budget - total
            tails = {"hindi": f" बजट बचा: ~{left}।", "hinglish": f" Budget bacha: ~{left}.",
                     "english": f" Budget left: ~{left}."}[lang]
        else:
            tails = ""
        body = {
            "hindi":    f"आज तक {n} मील में ~{total} कैलोरी।{tails}",
            "hinglish": f"Aaj tak {n} meal mein ~{total} cal.{tails}",
            "english":  f"Today: ~{total} cal across {n} meals.{tails}",
        }[lang]
        return {"reply": body, "today_total": [total, total],
                "budget_left": ([budget - total] if budget is not None else None)}

    def _handle_recommend(self, user_input, context):
        """Constraint solver: parse food + cal/protein limits, search the CSV."""
        lang = detect_language(user_input)
        food, max_cal, min_protein = fm_recommend.parse_constraints(
            user_input, self.food_vocab)
        if not food or not max_cal:
            ask = {
                "hindi":    "बताओ कौन सा खाना, कितनी कैलोरी और प्रोटीन? जैसे '250 cal me paneer, 12g protein'।",
                "hinglish": "Bata kaun sa khana, kitni cal aur protein? Jaise '250 cal me paneer, 12g protein'.",
                "english":  "Tell me the food, calorie limit, and protein target. e.g. '250 cal paneer with 12g protein'.",
            }[lang]
            return {"reply": ask}
        recs = fm_recommend.recommend(food, max_cal, min_protein, self.hybrid.db)
        reply = fm_recommend.build_reply(food, max_cal, min_protein, recs, lang)
        return {"reply": reply, "recommendations": recs}

    def _handle_help(self, user_input):
        """Clarification fallback: acknowledge the miss and surface the
        supported actions as examples (not a dead-end). Includes quick-reply
        chips the frontend can render as tappable buttons."""
        lang = detect_language(user_input)
        msg = {
            "hindi": ("समझ नहीं आया 🤔 मैं ये कर सकता हूँ:\n"
                      "• खाना लॉग करो — \"2 रोटी और दाल\"\n"
                      "• आज का टोटल — \"आज कितना खाया\"\n"
                      "• सुझाव — \"250 cal में पनीर, 12g protein\""),
            "hinglish": ("Samajh nahi aaya 🤔 Main ye kar sakta hun:\n"
                         "• Khana log karo — \"2 roti aur dal\"\n"
                         "• Aaj ka total — \"aaj kitna khaya\"\n"
                         "• Suggestion — \"250 cal me paneer, 12g protein\""),
            "english": ("Didn't quite get that 🤔 Here's what I can do:\n"
                        "• Log food — \"2 roti and dal\"\n"
                        "• Today's total — \"how much have I eaten\"\n"
                        "• Suggest a meal — \"paneer under 250 cal with 12g protein\""),
        }[lang]
        chips = {
            "hindi":    ["2 रोटी दाल", "आज कितना खाया", "250 cal में पनीर"],
            "hinglish": ["2 roti dal", "aaj kitna khaya", "250 cal me paneer 12g protein"],
            "english":  ["2 roti and dal", "how much have I eaten", "paneer under 250 cal 15g protein"],
        }[lang]
        return {"reply": msg, "chips": chips}


if __name__ == "__main__":
    import tempfile, os
    # fresh temp DB so the demo is repeatable
    db = os.path.join(tempfile.gettempdir(), "fm_engine_demo.db")
    if os.path.exists(db):
        os.remove(db)

    # MOCK model -> tests the whole pipeline without needing the GGUF locally
    engine = FitMindEngine(mock=True, db_path=db)

    print("=" * 60)
    print("ENGINE END-TO-END DEMO (mock model)")
    print("=" * 60)

    print("\n--- Meal 1: subah ---")
    r1 = engine.process("abhi maine 3 roti aur ek bowl rajma khaya", user_id=1)
    print("calories:", r1["calories"], " protein:", r1["protein_g"], "g")
    print("today_total:", r1["today_total"], " budget_left:", r1["budget_left"])
    print("matched:", r1["_meta"]["matched_items"])

    print("\n--- Meal 2: lunch (memory should add up) ---")
    r2 = engine.process("lunch mein 2 samosa khaye", user_id=1)
    print("calories:", r2["calories"], " protein:", r2["protein_g"], "g")
    print("today_total:", r2["today_total"], " budget_left:", r2["budget_left"])
    print("  ^ today_total should include meal 1 + meal 2")
