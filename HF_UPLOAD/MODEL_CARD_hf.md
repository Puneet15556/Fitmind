---
license: apache-2.0
base_model: Qwen/Qwen3-1.7B
tags:
  - calorie-tracking
  - indian-food
  - qlora
  - gguf
  - edge
language:
  - en
  - hi
pipeline_tag: text-generation
---

# FitMind-Qwen3-1.7B (fine-tuned)

A Qwen3-1.7B fine-tuned to extract Indian food items and estimate nutrition
from English / Hindi / Hinglish text. Quantized to **Q4_K_M GGUF** (~1.1 GB)
for offline, on-device inference.

> On the Hub: rename this file to `README.md` in the model repo.

## Training
- **Base:** Qwen/Qwen3-1.7B
- **Method:** QLoRA (4-bit NF4 base, LoRA r=16, alpha=32, all linear layers)
- **Hardware:** single T4 (Colab), 3 epochs, ~2-3 hours
- **Dataset:** 772 trilingual examples — 30 hand-written gold + 588 programmatic
  (generated from a 348-food nutrition table) + 154 distilled from Llama-3.3-70B.
  Balanced 35/33/32 % across English / Hindi / Hinglish.

## Results (held-out test set, 38 examples)
| Metric | Score |
|--------|-------|
| Token accuracy (train) | ~94 % |
| Valid JSON output | 100 % |
| Item extraction | 89 % |
| Language match | 74 % |
| Calorie MAE | ~122 cal |

> The deployed app pairs this model with a deterministic **hybrid layer** that
> replaces the model's estimated numbers with exact CSV lookups — so end-user
> calorie/macro accuracy does not depend on the model's numeric estimates.

## Files
- `fitmind-Q4_K_M.gguf` — quantized model for llama.cpp / Ollama / llama.rn
- `adapter/` — the raw LoRA adapter (training output)

## Usage (Ollama)
```bash
ollama create fitmind -f Modelfile     # Modelfile: FROM ./fitmind-Q4_K_M.gguf
ollama run fitmind
```

Code + live demo: [GitHub] · [HF Space]
