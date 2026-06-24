"""
FitMind memory — SQLite store for meals + user profile.

This is the "running total" brain. The SLM is stateless; this remembers what
the user ate today so the engine can inject it as context (prior meals,
total_cal_so_far, budget) into each request.

Tables:
  profile : one row per user (daily calorie budget, goal)
  meals   : one row per logged meal (timestamp, items, calories, macros)

Key methods:
  get_today(user_id)  -> context dict for the engine/prompt
  save_meal(user_id, result) -> persist a processed meal
"""

import sqlite3
import json
from datetime import date
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "fitmind.db"


class MealMemory:
    def __init__(self, db_path=DEFAULT_DB, default_budget=2000):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.default_budget = default_budget
        self._init_db()

    def _conn(self):
        # one connection per call keeps it simple + thread-safe enough for v1
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    user_id      INTEGER PRIMARY KEY,
                    daily_budget INTEGER DEFAULT 2000,
                    goal         TEXT DEFAULT 'maintain'
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS meals (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    day       TEXT NOT NULL,           -- YYYY-MM-DD
                    ts        TEXT DEFAULT CURRENT_TIMESTAMP,
                    raw_input TEXT,
                    items     TEXT,                    -- JSON list
                    cal_min   INTEGER,
                    cal_max   INTEGER,
                    protein_g REAL,
                    carbs_g   REAL,
                    fat_g     REAL,
                    fiber_g   REAL
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_meals_user_day ON meals(user_id, day)")

    # ---- profile ----------------------------------------------------
    def set_budget(self, user_id, budget, goal="maintain"):
        with self._conn() as c:
            c.execute(
                "INSERT INTO profile(user_id, daily_budget, goal) VALUES(?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET daily_budget=?, goal=?",
                (user_id, budget, goal, budget, goal))

    def get_budget(self, user_id):
        """Return the user's budget, or None if they haven't set one yet."""
        with self._conn() as c:
            row = c.execute("SELECT daily_budget FROM profile WHERE user_id=?",
                            (user_id,)).fetchone()
        return row["daily_budget"] if row else None

    # ---- the context the engine needs -------------------------------
    def get_today(self, user_id, today=None):
        """Return {today_meals, total_cal_so_far, budget} for prompt injection."""
        today = today or date.today().isoformat()
        with self._conn() as c:
            rows = c.execute(
                "SELECT raw_input, cal_min, cal_max FROM meals "
                "WHERE user_id=? AND day=? ORDER BY id", (user_id, today)).fetchall()

        meals = [{"meal": r["raw_input"], "cal": [r["cal_min"], r["cal_max"]]}
                 for r in rows]
        # running total uses the midpoint of each meal's range
        total = sum((r["cal_min"] + r["cal_max"]) // 2 for r in rows)
        return {
            "today_meals": meals,
            "total_cal_so_far": total,
            "budget": self.get_budget(user_id),
        }

    # ---- persist a processed meal -----------------------------------
    def save_meal(self, user_id, raw_input, result, today=None):
        today = today or date.today().isoformat()
        out = result
        cal = out.get("calories", [0, 0])
        with self._conn() as c:
            c.execute(
                "INSERT INTO meals(user_id, day, raw_input, items, cal_min, cal_max, "
                "protein_g, carbs_g, fat_g, fiber_g) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (user_id, today, raw_input,
                 json.dumps(out.get("items", []), ensure_ascii=False),
                 cal[0], cal[1],
                 out.get("protein_g", 0), out.get("carbs_g", 0),
                 out.get("fat_g", 0), out.get("fiber_g", 0)))

    # ---- helpers ----------------------------------------------------
    def reset_day(self, user_id, today=None):
        today = today or date.today().isoformat()
        with self._conn() as c:
            c.execute("DELETE FROM meals WHERE user_id=? AND day=?", (user_id, today))


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    # quick self-test (temp file — :memory: doesn't persist across connections)
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), "fm_test.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    mem = MealMemory(db_path=tmp)
    mem.set_budget(1, 2000)
    print("Empty context:", mem.get_today(1))

    mem.save_meal(1, "3 paratha", {"calories": [510, 660], "protein_g": 12,
                                   "carbs_g": 66, "fat_g": 36, "fiber_g": 6,
                                   "items": [{"name": "paratha", "qty": 3}]})
    print("After 1 meal:  ", mem.get_today(1))

    mem.save_meal(1, "2 roti dal", {"calories": [300, 370], "protein_g": 14,
                                    "carbs_g": 50, "fat_g": 7, "fiber_g": 9,
                                    "items": [{"name": "roti", "qty": 2}]})
    ctx = mem.get_today(1)
    print("After 2 meals: ", ctx)
    print(f"\nRunning total: {ctx['total_cal_so_far']} cal, "
          f"budget left ~{ctx['budget'] - ctx['total_cal_so_far']}")
