# FitMind — self-contained backend image.
# Bundles the model + hybrid + UI; runs the GGUF in-process via llama-cpp-python
# (no Ollama needed inside the container -> "pull once, run anywhere/offline").
#
# Build:  docker build -t fitmind .
# Run:    docker run -p 8000:8000 fitmind
# Open:   http://localhost:8000

FROM python:3.12-slim

# build tools (llama-cpp-python may compile a CPU build for this container)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY scripts/ ./scripts/
COPY web/ ./web/

# data + model (the CSV the hybrid/recommender need + the fine-tuned GGUF)
COPY data/processed/nutrition.csv ./data/processed/nutrition.csv
COPY models/fitmind-Q4_K_M.gguf ./models/fitmind-Q4_K_M.gguf

# run the GGUF in-process (no Ollama daemon in the container)
ENV FITMIND_BACKEND=llamacpp
ENV FITMIND_MODEL=/app/models/fitmind-Q4_K_M.gguf
ENV FITMIND_CSV=/app/data/processed/nutrition.csv

EXPOSE 8000
WORKDIR /app/scripts
CMD ["uvicorn", "fm_api:app", "--host", "0.0.0.0", "--port", "8000"]
