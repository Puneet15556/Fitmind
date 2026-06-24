"""
FitMind backend — FastAPI server wrapping the engine.

This is the SINGLE backend any client (web app, phone, watch) calls.
It contains the model (via Ollama) + hybrid correction + memory, behind one API.

Endpoints:
  GET  /health              -> is the server up + model reachable
  POST /log-meal            -> log a meal, get exact corrected nutrition
  GET  /today/{user_id}     -> today's running total + meals
  POST /profile             -> set a user's daily budget
  POST /reset/{user_id}     -> clear today's meals

Run:
  uvicorn fm_api:app --reload --port 8000      (from the scripts/ dir)
  or: python scripts/fm_api.py

Then open http://localhost:8000/docs for an interactive API tester.

Storage is SQLite for v1 (swap to Supabase for cloud multi-user in v2).
The engine + DB are created ONCE at startup and reused across requests.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fm_engine import FitMindEngine
from fm_calories import calc_budget

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# --- one engine for the whole server (loaded once) -------------------
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "fitmind_api.db"
# Configurable via env vars (Docker sets these):
#   FITMIND_BACKEND = ollama (local dev) | llamacpp (Docker/cloud, self-contained)
#   FITMIND_MODEL   = path to the GGUF (only needed for llamacpp)
BACKEND = os.environ.get("FITMIND_BACKEND", "ollama")
MODEL_PATH = os.environ.get("FITMIND_MODEL",
                            str(ROOT / "models" / "fitmind-Q4_K_M.gguf"))
CSV_PATH = os.environ.get("FITMIND_CSV",
                          str(ROOT / "data" / "processed" / "nutrition.csv"))
engine: FitMindEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = FitMindEngine(backend=BACKEND, model_path=MODEL_PATH,
                           csv_path=CSV_PATH, db_path=str(DB_PATH))
    yield
    # (nothing to clean up)


app = FastAPI(title="FitMind API", version="1.0", lifespan=lifespan)

# allow the browser frontend to call the API (CORS)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def home():
    """Serve the chat web UI."""
    return FileResponse(WEB_DIR / "index.html")


# --- request/response shapes (Pydantic validates incoming JSON) ------
class MealRequest(BaseModel):
    user_id: int = Field(default=1, description="authenticated user id")
    text: str = Field(description="what the user ate, any language")


class ProfileRequest(BaseModel):
    user_id: int = 1
    daily_budget: int = 2000
    goal: str = "maintain"


class CalcRequest(BaseModel):
    user_id: int = 1
    age: int = Field(ge=10, le=100)
    weight_kg: float = Field(gt=20, lt=300)
    height_cm: float = Field(gt=100, lt=250)
    gender: str = "male"
    activity: str = "moderate"
    goal: str = "maintain"


# --- endpoints -------------------------------------------------------
@app.get("/health")
def health():
    """Quick check that the server and model are reachable."""
    try:
        # tiny model ping via the engine's model wrapper
        ok = True
        backend = engine.model.backend
    except Exception as e:
        raise HTTPException(503, f"engine not ready: {e}")
    return {"status": "ok", "model_backend": backend}


@app.post("/log-meal")
def log_meal(req: MealRequest):
    """Log a meal -> returns exact (hybrid-corrected) nutrition + running total."""
    result = engine.process(req.text, user_id=req.user_id)
    if "error" in result:
        raise HTTPException(422, result["error"])
    # strip internal _meta before returning (keep response clean)
    meta = result.pop("_meta", {})
    result["language"] = meta.get("target_lang")
    result["unmatched_items"] = meta.get("unmatched_items", [])
    return result


@app.get("/today/{user_id}")
def today(user_id: int):
    """Today's running total + the meals logged so far.
    budget / budget_left are null if the user hasn't set a budget yet."""
    ctx = engine.memory.get_today(user_id)
    budget = ctx["budget"]
    return {
        "user_id": user_id,
        "total_cal_so_far": ctx["total_cal_so_far"],
        "budget": budget,
        "budget_left": (budget - ctx["total_cal_so_far"]) if budget is not None else None,
        "budget_set": budget is not None,
        "meals": ctx["today_meals"],
    }


@app.post("/profile")
def set_profile(req: ProfileRequest):
    """Set a user's daily calorie budget."""
    engine.memory.set_budget(req.user_id, req.daily_budget, req.goal)
    return {"user_id": req.user_id, "daily_budget": req.daily_budget, "goal": req.goal}


@app.post("/calculate-budget")
def calculate_budget(req: CalcRequest):
    """Compute a personalized calorie budget (BMR/TDEE) and save it as the
    user's daily budget. Returns the full breakdown."""
    result = calc_budget(req.age, req.weight_kg, req.height_cm,
                         req.gender, req.activity, req.goal)
    engine.memory.set_budget(req.user_id, result["daily_budget"], req.goal)
    result["user_id"] = req.user_id
    return result


@app.post("/reset/{user_id}")
def reset(user_id: int):
    """Clear today's meals for a user."""
    engine.memory.reset_day(user_id)
    return {"user_id": user_id, "status": "today cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
