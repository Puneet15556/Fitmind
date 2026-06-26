# FitMind 💪 — Offline AI Calorie Tracker for Indian Gym Users

> Fine-tuned **Qwen3-1.7B** (QLoRA → Q4_K_M GGUF) that logs Indian food in
> **English / Hindi / Hinglish** and returns **exact** calories & macros — fully
> offline, with a deterministic hybrid correction layer, intent routing, a
> personalized BMR/TDEE budget, and a constraint-solver meal recommender.

`SLM` · `QLoRA` · `GGUF` · `quantization` · `edge-AI` · `on-device` ·
`llama.cpp` · `Ollama` · `FastAPI` · `RAG` · `Qwen3` · `fine-tuning`

---

## 📱 What's an SLM (and why it matters here)?

A **Small Language Model** (~1–3B parameters) is compact enough to run
**directly on the device** — a phone, a laptop, even a wearable — using only the
local CPU/NPU chipset, with **no cloud GPU**. After 4-bit quantization,
Qwen3-1.7B shrinks to ~1.1 GB and runs on a phone's chipset (e.g. Snapdragon
/ Apple Neural Engine) **entirely offline**.

That's the whole point of FitMind: an LLM-grade chatbot that works in a gym
basement with zero signal — fast, private (data never leaves the device), and
free to run (no per-request API cost). The trade-off is size, which is exactly
what fine-tuning + quantization solve.

---

## 🔗 Live demo & model

- **Live app (HF Space):** https://huggingface.co/spaces/Puneet666/fitmind
- **Model + adapter (HF Hub):** https://huggingface.co/Puneet666/fitmind-qwen-gguf

> ⚠️ The live Space runs on HuggingFace's **free CPU tier**, so each response
> takes ~20-40s. This is a **zero-cost public demo** to show the project is
> deployed and functional — *not* a performance target. The model is built for
> **on-device** inference (a phone's NPU ≈ 1-2s) or a GPU Space; on a laptop via
> Ollama it responds in ~5-15s (Based on your CPU).

---

## ✨ What it does

Type a meal in any language and get exact nutrition + a running daily total:

| You type | FitMind |
|----------|---------|
| `abhi 3 roti aur ek bowl rajma khaya` | `3 roti, 1 rajma = ~374-476 cal, protein 18.5g. Total aaj: ~374-476.` |
| `I had grilled chicken` | exact cal/protein from the nutrition table |
| `मैंने पोहा खाया` | replies in the same language |
| `aaj kitna khaya` | today's running total (no model call) |
| `250 cal me paneer 12g protein` | ranked portion suggestions that fit the limits |
| `hello` | a clarification with tappable quick-reply chips |

Core features:
- 🍛 **Trilingual food logging** — English / Hindi / Hinglish (code-mixed)
- 🎯 **Exact macros** — numbers come from a 348-food table, never hallucinated
- 📊 **Personalized budget** — Mifflin-St Jeor BMR → TDEE → goal pace, or set manually
- 💬 **Running daily total** — memory-aware, recomputes from the start of the day
- 🧮 **Meal recommender** — "what should I eat under X cal with Y g protein"
- 🌐 **Offline-first** — the model runs on-device; no internet for core features

---

## 🤔 Why Qwen3-1.7B?

| Need | Why Qwen3-1.7B |
|------|----------------|
| Hindi / Hinglish | Trained on 119 languages incl. strong Indic — handles code-mixing |
| Edge / phone | 1.7B → ~1.1 GB at Q4_K_M, fits low-end Android & runs on CPU |
| Licensing | Apache 2.0 — free for commercial / portfolio use |
| Instruction following | Strong structured-output behaviour at small size |
| Reasoning | Optional thinking mode (disabled here for fast JSON output) |

Considered Llama-3.2-1B (weaker Hindi), Gemma-2-2B (restrictive license),
Phi-3.5-mini (bigger). Qwen3-1.7B was the best size/multilingual/license fit.

---

## 🧠 Core principle: "tell, don't guess"

An SLM is great at language but unreliable at exact arithmetic. So the model
only does what it's good at — understanding messy multilingual text — and
**deterministic code handles every number**:

- **Calories / macros** → exact CSV lookup (not the model's estimate)
- **Daily total** → summed from memory
- **Budget** → BMR/TDEE formula
- **Recommendations** → constraint solver over the table
- **Reply text** → built from the corrected numbers, in the user's language

This guarantees numerical accuracy **regardless of model size or quantization**.

---

## 🏗️ Architecture

```
                 user message (any language)
                          │
            ┌─────────────▼─────────────┐
            │  INTENT ROUTER            │  rules first (fast, free),
            │  log / query / recommend  │  SLM fallback for ambiguous
            │  / help                   │
            └──┬───────┬───────┬────────┘
               │       │       │        │
        ┌──────▼─┐ ┌───▼───┐ ┌─▼──────┐ ┌▼─────────┐
        │  LOG   │ │ QUERY │ │RECOMMEND│ │  HELP    │
        │        │ │       │ │         │ │          │
        │ model  │ │memory │ │constraint│ │clarify + │
        │ +hybrid│ │ only  │ │ solver  │ │ chips    │
        │ +memory│ │(no AI)│ │ (no AI) │ │ (no AI)  │
        └────┬───┘ └───────┘ └─────────┘ └──────────┘
             │
     ┌───────▼──────────────────────────────────┐
     │  LOG pipeline                             │
     │  1. memory → today's context              │
     │  2. SLM (Qwen via Ollama/llama.cpp)       │
     │     → extract items + language            │
     │  3. parse JSON (strip <think>)            │
     │  4. HYBRID → exact CSV numbers + reply    │
     │  5. memory.save → running total           │
     │  + safety net: no food found → clarify    │
     └───────────────────────────────────────────┘
```

**The model is stateless; the app manages routing, memory, and all math.**

---

## 🔬 The hybrid layer (key innovation)

Not RAG (no LLM in the loop) — a deterministic corrector:

1. **Lookup** — each extracted item → nutrition table (O(1) hash match, then
   word-overlap fuzzy match for plurals / word order).
2. **Compute** — `value × quantity`, summed; calories as a ±12% range, macros exact.
3. **Recompute totals** — `today_total = prev + calories`, `budget_left = budget - today`.
4. **Build reply** — fill a per-language template with the exact numbers (this also
   removes any need to translate — the reply is built in the target language).

Example: the model estimated **12g protein** for *3 roti + rajma*; the hybrid
corrects it to the exact **18.5g** (3×2.5 + 11). Model-agnostic — the same layer
wraps the FP16, GGUF, or cloud model, and ports to JS for the offline phone build.

---

## 🗂️ Project structure (what each folder does)

```
fitmind/
├── scripts/          all Python code
│   │  ── RUNTIME (the running app) ──
│   ├── fm_api.py        FastAPI backend — endpoints + serves the web UI
│   ├── fm_engine.py     orchestrator — intent routing + handlers
│   ├── fm_model.py      model wrapper (mock / Ollama / llama.cpp) + JSON parser
│   ├── hybrid.py        CSV exact-lookup + reply builder (the corrector)
│   ├── fm_memory.py     SQLite — running daily total
│   ├── fm_intent.py     intent router (rules + SLM fallback)
│   ├── fm_recommend.py  constraint-solver meal recommender
│   ├── fm_calories.py   BMR/TDEE personalized budget calculator
│   ├── fm_chat.py       interactive terminal client (dev)
│   │  ── BUILD-TIME (data pipeline, run once) ──
│   ├── seed_nutrition.py / seed_nutrition_extra.py   build the 348-food table
│   ├── gold_examples.py            30 hand-written examples
│   ├── generate_examples.py        300 programmatic single-item examples
│   ├── generate_combos.py          288 programmatic thali/combo examples
│   ├── generate_groq.py            distill examples from Llama-3.3-70B (Groq)
│   ├── clean_groq.py               validate/clean distilled output
│   ├── merge_split.py              merge all → train/val/test split
│   ├── to_chat_format.py           convert to Qwen chat format
│   └── test_hybrid.py              hybrid unit tests
├── web/
│   └── index.html      chat UI — progress bar, ⚙️ settings, quick-reply chips
├── data/processed/
│   ├── nutrition.csv   348-food nutrition table (the lookup source)
│   ├── *.jsonl         dataset: gold/generated/combo/groq + train/val/test
├── colab/
│   ├── fitmind_train.ipynb   QLoRA fine-tuning notebook (training proof)
│   └── fitmind_gguf.ipynb    merge → GGUF → quantize notebook
├── models/             (gitignored) GGUF + Ollama Modelfile — model is on HF Hub
├── HF_UPLOAD/          HuggingFace Spaces deploy files (Dockerfile, README, card)
├── Dockerfile          containerized backend (local, port 8000)
├── requirements.txt    runtime dependencies
└── .gitignore          excludes the model, .env, and DB files
```

---

## 📊 Dataset (772 trilingual examples)

Three techniques combined:

| Source | Count | How |
|--------|-------|-----|
| Manual gold | 30 | hand-written premium examples |
| Programmatic (single) | 300 | iterate the nutrition table, exact math, templated phrasings |
| Programmatic (combos) | 288 | realistic thali combinations, summed nutrition |
| **Distillation** | 154 | Llama-3.3-70B (free via Groq) generates natural Hinglish examples, then validated/cleaned |

Balanced 35 / 33 / 32 % across English / Hindi / Hinglish. Each example carries a
memory context (prior meals, running total, budget). Split 696 / 38 / 38.

---

## 🏋️ Training & quantization

- **Method:** QLoRA — 4-bit NF4 base, LoRA `r=16, alpha=32` on all linear layers
- **Hardware:** single T4 (Colab), 3 epochs, ~2-3 hours
- **Result:** ~94 % token accuracy, val loss 0.19
- **Quantization:** merge LoRA → FP16 → `llama.cpp` → **Q4_K_M GGUF (~1.1 GB)**
  (compared Q4_K_M / Q5_K_M / Q6_K against the FP16 baseline)

---

## 🧪 Evaluation & test cases

**Held-out test set (38 unseen examples):**

| Metric | Score | Meaning |
|--------|-------|---------|
| Valid JSON | 100 % | app never fails to parse |
| Item extraction | 89 % | correct foods identified (what the hybrid relies on) |
| Language match | 74 % | reply in the input language (then forced exact by the reply builder) |
| Calorie MAE | ~122 cal | model's raw estimate error — **made 0 by the hybrid** |

**Unit tests:** `hybrid` 25/25 · `intent` 10/10 · `calories` 6/6

**Behavioural test cases handled:**
- Log: `2 roti dal khaya`, `I had paneer tikka`, `मैंने 3 पराठा खाए`
- Memory: second meal adds to the first (running total)
- Query: `aaj kitna khaya` → answered from memory, no model call
- Recommend: `250 cal paneer 12g protein` → ranked portions
- Budget not set → bar hidden, total only; once set → recomputed for the whole day
- Greeting / gibberish → routed to clarification (safety net), never a garbage meal
- Wrong-language reply → reply rebuilt in the target language

---

## 🚀 Run it

### Local (Ollama — recommended on Windows/Mac)
```bash
# 1. import the model into Ollama (Modelfile: FROM ./fitmind-Q4_K_M.gguf)
ollama create fitmind -f models/Modelfile

# 2. start the backend
pip install -r requirements.txt
cd scripts && python fm_api.py

# 3. open the app
#    http://localhost:8000
```

### Docker (self-contained, runs the GGUF in-process via llama.cpp)
```bash
docker build -t fitmind .
docker run -p 8000:8000 fitmind
# open http://localhost:8000
```

---

## 🌍 Deployment & distribution

Distribution is **audience-specific** — the same engine deploys three ways:

### 1. Online demo (web) — for recruiters / quick access
Deployed as a **HuggingFace Space (Docker SDK)**: the container downloads the
model from the HF Hub and serves the backend + UI on a public URL. This is the
proof-of-work live demo — anyone opens the link, no install.
- Model artifact + card live on the **HF Hub** (the fine-tuning proof).
- The Space pulls the model from the Hub at build time.

### 2. Laptop-to-laptop (Docker registry)
The backend is a self-contained image — build once, run anywhere:
```bash
# build + push (machine A)
docker build -t <user>/fitmind .
docker push <user>/fitmind

# pull + run (machine B — only Docker required, no Python/Ollama/model setup)
docker pull <user>/fitmind
docker run -p 8000:8000 <user>/fitmind
```
For air-gapped transfer: `docker save fitmind -o fitmind.tar` → copy → `docker load`.

### 3. Mobile app (offline, on-device) — the offline-first vision
A React Native app bundling the model via **llama.rn**, the hybrid logic ported
to JS, and the 18 KB nutrition table — fully offline, no server. Distributed as a
signed **APK** (sideload for demo; Play Store for public release). The intent
router, hybrid layer, and recommender are device-local, so logging, calories, and
recommendations work with zero connectivity.

---

## 🗺️ Planned Improvements

- **Ingredient-level breakdown:** decompose composite dishes into ingredients
  (e.g. `3 egg fried rice` → 3 eggs + rice, `shake with seeds + peanut butter` →
  each ingredient) for finer accuracy — via a recipe map or decomposition-tuned
  training. Currently such a dish is matched as a single item.
- **GPU / on-device inference:** the free CPU Space is a demo; production targets
  a GPU Space or the phone's NPU for ~1-2s responses.

- **Cloud sync (Supabase):** Postgres + Auth + Row-Level-Security keyed on
  `user_id` (not IP) for multi-device sync — offline-first with opportunistic sync.
- **Mobile APK:** offline React Native build (llama.rn + JS hybrid).
- **Wearable OS:** WearOS / watch integration — a thin client that bridges to the
  phone over Bluetooth (primary) with cloud inference fallback, since watches
  can't run the model locally.

---

## 🔌 API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET`  | `/health` | server + model-backend status |
| `POST` | `/log-meal` | route a message → exact nutrition / answer |
| `GET`  | `/today/{user_id}` | running total + meals (budget null if unset) |
| `POST` | `/profile` | set a manual daily budget |
| `POST` | `/calculate-budget` | BMR/TDEE personalized budget |
| `POST` | `/reset/{user_id}` | clear today |

Interactive docs at `/docs` (FastAPI auto-generated).

---

## 🧱 Tech stack

Qwen3-1.7B · PEFT/QLoRA · llama.cpp (GGUF) · Ollama / llama-cpp-python ·
FastAPI · SQLite · vanilla JS · Docker · HuggingFace Hub & Spaces.

---

## 📄 License

Code: MIT. Model: Apache 2.0 (inherits Qwen3). Nutrition values cross-checked
against IFCT 2017 / USDA — estimates, not medical advice.
