# food/db.py

from pathlib import Path
import sqlite3
from typing import List, Tuple, Optional, Dict, Any

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "food_planner.db"

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def _table_info(conn: sqlite3.Connection, table: str):
    return conn.execute(f"PRAGMA table_info({table});").fetchall()

def delete_recipe(recipe_id: int) -> None:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    con.commit()
    con.close()
    
def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                ingredients TEXT,
                steps TEXT,
                tags TEXT,
                prep_minutes INTEGER DEFAULT 0,
                cook_minutes INTEGER DEFAULT 0,
                servings INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

        # (Optional) old-schema migration kept from earlier messages — safe to omit if fresh DB
        info = _table_info(conn, "recipes")
        if info:
            col = {row[1]: row for row in info}
            needs_migration = any(col.get(n, (None, None, None, 0))[3] == 1 for n in ("ingredients", "steps"))
            if needs_migration:
                conn.execute("BEGIN;")
                conn.execute(
                    """
                    CREATE TABLE recipes_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        ingredients TEXT,
                        steps TEXT,
                        tags TEXT,
                        prep_minutes INTEGER DEFAULT 0,
                        cook_minutes INTEGER DEFAULT 0,
                        servings INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT INTO recipes_new
                        (id, title, description, ingredients, steps, tags,
                         prep_minutes, cook_minutes, servings, created_at)
                    SELECT id, title, description, ingredients, steps, tags,
                           prep_minutes, cook_minutes, servings, created_at
                    FROM recipes;
                    """
                )
                conn.execute("DROP TABLE recipes;")
                conn.execute("ALTER TABLE recipes_new RENAME TO recipes;")
                conn.commit()

def add_recipe(
    title: str,
    description: str = "",
    ingredients: str = "",
    steps: str = "",
    tags: str = "",
    prep_minutes: int = 0,
    cook_minutes: int = 0,
    servings: int = 1,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO recipes
                (title, description, ingredients, steps, tags,
                 prep_minutes, cook_minutes, servings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (title or "").strip(),
                (description or "").strip(),
                (ingredients or "").strip(),
                (steps or "").strip(),
                (tags or "").strip(),
                int(prep_minutes or 0),
                int(cook_minutes or 0),
                int(servings or 1),
            ),
        )
        conn.commit()
        return cur.lastrowid

def update_recipe(
    recipe_id: int,
    title: str,
    description: str = "",
    ingredients: str = "",
    steps: str = "",
    tags: str = "",
    prep_minutes: int = 0,
    cook_minutes: int = 0,
    servings: int = 1,
) -> int:
    """Update a recipe. Returns number of rows affected (0 or 1)."""
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE recipes
            SET title = ?, description = ?, ingredients = ?, steps = ?, tags = ?,
                prep_minutes = ?, cook_minutes = ?, servings = ?
            WHERE id = ?
            """,
            (
                (title or "").strip(),
                (description or "").strip(),
                (ingredients or "").strip(),
                (steps or "").strip(),
                (tags or "").strip(),
                int(prep_minutes or 0),
                int(cook_minutes or 0),
                int(servings or 1),
                int(recipe_id),
            ),
        )
        conn.commit()
        return cur.rowcount

def list_recipes(limit: int = 100, search: Optional[str] = None) -> List[Tuple]:
    with _connect() as conn:
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """
                SELECT id, title, tags, servings, prep_minutes, cook_minutes, created_at
                FROM recipes
                WHERE title LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, title, tags, servings, prep_minutes, cook_minutes, created_at
                FROM recipes
                ORDER BY created_at DESC, id DESC
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
    keys = [
        "id","title","description","ingredients","steps","tags",
        "prep_minutes","cook_minutes","servings","created_at"
    ]
    return dict(zip(keys, row))
