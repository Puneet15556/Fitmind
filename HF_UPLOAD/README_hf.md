---
title: FitMind
emoji: 💪
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# FitMind 💪 — Offline Calorie Tracker for Indian Gym Users

A fine-tuned **Qwen3-1.7B** (QLoRA → Q4_K_M GGUF) that logs Indian food in
English / Hindi / Hinglish and returns **exact** calories + macros, with a
running daily total, a personalized BMR/TDEE budget, and a meal recommender.

**Type a meal** in the chat — e.g. `2 roti aur dal`, `I had grilled chicken`,
`मैंने पोहा खाया` — or ask `250 cal me paneer 12g protein`.

## How it works
- **Model** (Qwen3-1.7B, fine-tuned) extracts food items + language.
- **Hybrid layer** replaces the model's guessed numbers with exact values from
  a 348-food nutrition table (deterministic — no hallucinated calories).
- **Intent router** (rules + model fallback) dispatches to log / query /
  recommend / help handlers.
- **Recommender** is a constraint solver over the nutrition table.
- **Memory** (SQLite) keeps the running daily total.

The model runs **in-process via llama-cpp-python** — the same engine runs
offline on a laptop (Ollama) or on-device on a phone (llama.rn).

Model: [Hub link]  ·  Code: [GitHub link]
