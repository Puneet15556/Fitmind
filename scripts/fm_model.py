"""
FitMind model wrapper + output parser.

FitMindModel:
  - loads the GGUF via llama-cpp-python (real mode)
  - OR runs in mock mode (no model needed — returns canned output for testing)
  - generate(system, user) -> raw text
  - translate(text, lang)  -> re-express reply in target language (2nd model call,
                              used only by the hybrid translate fallback)
  - thinking is DISABLED ("/no_think") for fast structured output

parse_model_output(raw):
  - strips Qwen3's <think>...</think> block
  - extracts the JSON object
  - returns dict or None
"""

import re
import json


# ----------------------------------------------------------------------
# Parser — strip <think> and pull out the JSON
# ----------------------------------------------------------------------
def parse_model_output(raw):
    """Return parsed dict from the model's raw text, or None if no valid JSON."""
    if not raw:
        return None
    # 1. remove <think>...</think> (Qwen3 thinking blocks, even if empty)
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # 2. grab the outermost {...}
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


# ----------------------------------------------------------------------
# Model wrapper
# ----------------------------------------------------------------------
class FitMindModel:
    """Backends:
       mock      -> no model, canned output (logic testing)
       ollama    -> calls a local Ollama server (cross-platform, no AVX issues)
       llamacpp  -> llama-cpp-python in-process (may crash on some CPUs)
    """
    def __init__(self, model_path=None, mock=False, backend="ollama",
                 ollama_model="fitmind", ollama_host="http://localhost:11434",
                 n_ctx=1024):
        self.mock = mock
        self.backend = "mock" if mock else backend
        self.ollama_model = ollama_model
        self.ollama_host = ollama_host
        self.model_path = model_path
        self._llm = None
        if self.backend == "llamacpp":
            from llama_cpp import Llama
            self._llm = Llama(model_path=model_path, n_ctx=n_ctx, verbose=False)

    def _ollama_chat(self, messages, max_tokens=300):
        import requests
        resp = requests.post(
            f"{self.ollama_host}/api/chat",
            json={
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
                "think": False,                       # disable Qwen3 thinking
                "options": {"temperature": 0, "num_predict": max_tokens},
            }, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def generate(self, system, user, max_tokens=300):
        if self.backend == "mock":
            return self._mock_response(user)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        if self.backend == "ollama":
            return self._ollama_chat(messages, max_tokens)
        # llamacpp
        out = self._llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=0)
        return out["choices"][0]["message"]["content"]

    def classify_intent(self, text):
        """Ask the SLM to classify an ambiguous message into one intent word.
        Used only as a fallback when the keyword rules are unsure."""
        if self.backend == "mock":
            # cheap heuristic so tests/mock work without a real model
            t = text.lower()
            if any(w in t for w in ["suggest", "recommend", "what should", "kya khau"]):
                return "recommend"
            if any(w in t for w in ["total", "how much", "kitna"]):
                return "query"
            if any(w in t for w in ["khaya", "ate", "had"]):
                return "log"
            return "help"
        prompt = ("Classify the user's message into exactly ONE word:\n"
                  "log (they ate something) | recommend (they want a food suggestion "
                  "with calorie/protein limits) | query (they ask their total/budget) | "
                  "help (anything else).\n"
                  f"Message: \"{text}\"\n"
                  "Answer with ONLY the one word.")
        if self.backend == "ollama":
            out = self._ollama_chat([{"role": "user", "content": prompt}], max_tokens=5)
        else:
            r = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5, temperature=0)
            out = r["choices"][0]["message"]["content"]
        out = out.strip().lower()
        for intent in ("recommend", "query", "log", "help"):
            if intent in out:
                return intent
        return "help"

    def translate(self, text, target_lang):
        """Re-express `text` in target_lang. Used by hybrid's translate fallback."""
        if self.backend == "mock":
            return f"[{target_lang}] {text}"
        prompt = (f"Translate this short calorie message into {target_lang}. "
                  f"Keep the SAME numbers, keep it short and natural. "
                  f"Reply ONLY with the translation:\n{text}")
        if self.backend == "ollama":
            return self._ollama_chat(
                [{"role": "user", "content": prompt}], max_tokens=200).strip()
        out = self._llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200, temperature=0)
        return out["choices"][0]["message"]["content"].strip()

    # ---- mock: a canned, deliberately-imperfect response ----
    def _mock_response(self, user):
        """Simulates the real model: extracts a couple known foods, guesses
        slightly-wrong numbers (like the real Q4 did) so the hybrid has work to do."""
        # only look at the NEW input (after "User (...):"), not the context block —
        # the real model is trained to extract just the current meal.
        if "User (" in user:
            text = user.rsplit("User (", 1)[-1].split(":", 1)[-1].lower()
        else:
            text = user.lower()
        items = []
        # crude keyword extraction to mimic the model
        for name, default_qty in [("roti", 2), ("rajma", 1), ("samosa", 2),
                                   ("paratha", 2), ("dal", 1), ("rice", 1),
                                   ("paneer", 1), ("chicken", 1), ("dosa", 1)]:
            m = re.search(r"(\d+)\s*" + name, text)
            if name in text:
                qty = int(m.group(1)) if m else default_qty
                items.append({"name": name, "qty": qty, "unit": "piece"})
        # deliberately wrong numbers (hybrid will fix)
        return json.dumps({
            "items": items,
            "calories": [300, 400],
            "protein_g": 13, "carbs_g": 40, "fat_g": 10, "fiber_g": 3,
            "today_total": [300, 400], "budget_left": [1600, 1700],
            "reply": "approx logged, numbers rough",
        }, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    # ---- test the parser on a Qwen3-style output with <think> ----
    raw_with_think = """<think>

</think>
{"items": [{"name": "roti", "qty": 3}], "calories": [320, 420], "reply": "ok"}"""
    parsed = parse_model_output(raw_with_think)
    print("Parser test:")
    print("  stripped <think>, got:", parsed)
    assert parsed is not None and parsed["items"][0]["name"] == "roti"
    print("  PASS\n")

    # ---- test the mock model ----
    m = FitMindModel(mock=True)
    raw = m.generate("system prompt", "abhi 3 roti aur ek bowl rajma khaya")
    print("Mock model output:", raw)
    p = parse_model_output(raw)
    print("Parsed items:", p["items"])
    print("Translate test:", m.translate("3 roti = 425 cal", "hinglish"))
