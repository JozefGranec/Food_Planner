from pathlib import Path
import sqlite3
from typing import List, Tuple, Optional, Dict, Any

# Where the DB file lives (./data/food_planner.db)
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "food_planner.db"

def _connect() -> sqlite3.Connection:
    # check_same_thread=False is helpful with Streamlit
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                ingredients TEXT NOT NULL,   -- newline separated
                steps TEXT NOT NULL,         -- newline separated
                tags TEXT,                   -- comma separated
                prep_minutes INTEGER DEFAULT 0,
                cook_minutes INTEGER DEFAULT 0,
                servings INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

def add_recipe(
    title: str,
    description: str,
    ingredients: str,
    steps: str,
    tags: str = "",
    prep_minutes: int = 0,
    cook_minutes: int = 0,
    servings: int = 1,
) -> int:
    """Insert a recipe and return its new id."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO recipes
                (title, description, ingredients, steps, tags, prep_minutes, cook_minutes, servings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, ingredients, steps, tags, prep_minutes, cook_minutes, servings),
        )
        conn.commit()
        return cur.lastrowid

def list_recipes(limit: int = 100, search: Optional[str] = None) -> List[Tuple]:
    """Return rows for display. If search is provided, filter by title or tags."""
    with _connect() as conn:
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """
                SELECT id, title, tags, servings, prep_minutes, cook_minutes, created_at
                FROM recipes
                WHERE title LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, title, tags, servings, prep_minutes, cook_minutes, created_at
                FROM recipes
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return rows

def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, title, description, ingredients, steps, tags,
                   prep_minutes, cook_minutes, servings, created_at
            FROM recipes WHERE id = ?
            """,
            (recipe_id,),
        ).fetchone()
    if not row:
        return None
    keys = ["id","title","description","ingredients","steps","tags",
            "prep_minutes","cook_minutes","servings","created_at"]
    return dict(zip(keys, row))
