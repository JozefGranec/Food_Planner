# food/db.py
"""
SQLite helpers for the Food Planner app.

Exports:
- init_db()
- add_recipe(title, ingredients="", instructions="")
- list_recipes(search: str | None = None) -> list[dict]
- get_recipe(recipe_id: int) -> dict | None
- update_recipe(recipe_id: int, title=None, ingredients=None, instructions=None)
- delete_recipe(recipe_id: int)
- count_recipes() -> int
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional, Dict

# --- Where the DB lives (same folder as this file) ---
DB_PATH = Path(__file__).with_suffix("").parent / "recipes.db"


# ---------- Low-level utilities ----------
def _dict_factory(cursor: sqlite3.Cursor, row: Iterable[Any]) -> Dict[str, Any]:
    """Return rows as dicts instead of tuples."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _connect() -> sqlite3.Connection:
    # Use default thread policy; Streamlit runs single-threaded per session.
    con = sqlite3.connect(DB_PATH)
    con.row_factory = _dict_factory
    return con


def _ensure_tables(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            ingredients TEXT,
            instructions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Lightweight indices (optional but nice as data grows)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title)")
    con.commit()


def _migrate_columns(con: sqlite3.Connection) -> None:
    """
    If an older DB exists (only 'title' column), add 'ingredients' and 'instructions'
    without dropping user data.
    """
    cur = con.cursor()
    cur.execute("PRAGMA table_info(recipes)")
    cols = {row["name"] for row in cur.fetchall()}
    changed = False

    if "ingredients" not in cols:
        cur.execute("ALTER TABLE recipes ADD COLUMN ingredients TEXT")
        changed = True
    if "instructions" not in cols:
        cur.execute("ALTER TABLE recipes ADD COLUMN instructions TEXT")
        changed = True
    if "created_at" not in cols:
        cur.execute("ALTER TABLE recipes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        changed = True
    if "updated_at" not in cols:
        cur.execute("ALTER TABLE recipes ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        changed = True

    if changed:
        con.commit()


# ---------- Public API ----------
def init_db() -> None:
    """
    Ensure the database exists, tables are created, and columns are up to date.
    Safe to call on every app load.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as con:
        # PRAGMAs: small durability/perf improvements
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA foreign_keys=ON;")
        _ensure_tables(con)
        _migrate_columns(con)


def add_recipe(title: str, ingredients: str = "", instructions: str = "") -> int:
    """
    Insert a new recipe and return its id.
    """
    if not title or not title.strip():
        raise ValueError("title is required")

    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO recipes (title, ingredients, instructions)
            VALUES (?, ?, ?)
            """,
            (title.strip(), ingredients.strip(), instructions.strip()),
        )
        con.commit()
        return int(cur.lastrowid)


def list_recipes(search: Optional[str] = None) -> list[dict]:
    """
    Return all recipes as a list of dicts, optionally filtered by a case-insensitive search
    in the title. Sorted alphabetically by title.
    """
    with _connect() as con:
        cur = con.cursor()
        if search and search.strip():
            like = f"%{search.strip().lower()}%"
            cur.execute(
                """
                SELECT id, title, ingredients, instructions, created_at, updated_at
                FROM recipes
                WHERE LOWER(title) LIKE ?
                ORDER BY LOWER(title) ASC
                """,
                (like,),
            )
        else:
            cur.execute(
                """
                SELECT id, title, ingredients, instructions, created_at, updated_at
                FROM recipes
                ORDER BY LOWER(title) ASC
                """
            )
        return cur.fetchall()  # list of dicts


def get_recipe(recipe_id: int) -> Optional[dict]:
    """Return a single recipe dict or None if not found."""
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, title, ingredients, instructions, created_at, updated_at
            FROM recipes
            WHERE id = ?
            """,
            (recipe_id,),
        )
        return cur.fetchone()


def update_recipe(
    recipe_id: int,
    title: Optional[str] = None,
    ingredients: Optional[str] = None,
    instructions: Optional[str] = None,
) -> None:
    """
    Update fields provided (title/ingredients/instructions).
    """
    if title is None and ingredients is None and instructions is None:
        return  # nothing to do

    sets = []
    params: list[Any] = []
    if title is not None:
        sets.append("title = ?")
        params.append(title.strip())
    if ingredients is not None:
        sets.append("ingredients = ?")
        params.append(ingredients.strip())
    if instructions is not None:
        sets.append("instructions = ?")
        params.append(instructions.strip())

    sets.append("updated_at = CURRENT_TIMESTAMP")
    sql = f"UPDATE recipes SET {', '.join(sets)} WHERE id = ?"
    params.append(recipe_id)

    with _connect() as con:
        cur = con.cursor()
        cur.execute(sql, tuple(params))
        con.commit()


def delete_recipe(recipe_id: int) -> None:
    """Delete a recipe by id."""
    with _connect() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        con.commit()


def count_recipes() -> int:
    """Return total number of recipes."""
    with _connect() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM recipes")
        row = cur.fetchone()
        return int(row["c"]) if row else 0
