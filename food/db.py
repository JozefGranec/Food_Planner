# food/db.py
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import sqlite3

# Check if running online with a DATABASE_URL env variable
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g., from Streamlit Secrets

USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

def _connect():
    """Return a DB connection depending on environment."""
    if USE_POSTGRES:
        con = psycopg2.connect(DATABASE_URL)
        # Dict cursor like sqlite3.Row
        con.cursor_factory = psycopg2.extras.RealDictCursor
        return con
    else:
        DB_PATH = Path("./food.sqlite3")
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        return con

def init_db() -> None:
    """Create table if needed."""
    con = _connect()
    cur = con.cursor()

    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                ingredients TEXT,
                instructions TEXT,
                image_bytes BYTEA,
                image_mime TEXT,
                image_filename TEXT,
                serves INTEGER
            );
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT,
                instructions TEXT,
                image_bytes BLOB,
                image_mime TEXT,
                image_filename TEXT,
                serves INTEGER
            );
        """)
    con.commit()
    con.close()


# ---------- CRUD Operations ----------

def add_recipe(
    title: str,
    ingredients: str = "",
    instructions: str = "",
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
    serves: Optional[int] = None,
) -> int:
    con = _connect()
    cur = con.cursor()
    if USE_POSTGRES:
        cur.execute(
            """
            INSERT INTO recipes (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
        )
        new_id = cur.fetchone()["id"]
    else:
        cur.execute(
            """
            INSERT INTO recipes (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
        )
        new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id


def list_recipes() -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT id, title, serves FROM recipes ORDER BY LOWER(title) ASC")
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]


def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    if USE_POSTGRES:
        cur.execute(
            "SELECT * FROM recipes WHERE id = %s", (recipe_id,)
        )
    else:
        cur.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        )
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def update_recipe(
    recipe_id: int,
    title: Optional[str] = None,
    ingredients: Optional[str] = None,
    instructions: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
    keep_existing_image: bool = True,
    serves: Optional[int] = None,
) -> None:
    con = _connect()
    cur = con.cursor()

    sets = []
    params: List[Any] = []

    if title is not None:
        sets.append("title = %s" if USE_POSTGRES else "title = ?")
        params.append(title)
    if ingredients is not None:
        sets.append("ingredients = %s" if USE_POSTGRES else "ingredients = ?")
        params.append(ingredients)
    if instructions is not None:
        sets.append("instructions = %s" if USE_POSTGRES else "instructions = ?")
        params.append(instructions)
    if serves is not None:
        sets.append("serves = %s" if USE_POSTGRES else "serves = ?")
        params.append(serves)

    if not keep_existing_image:
        sets += [
            "image_bytes = %s" if USE_POSTGRES else "image_bytes = ?",
            "image_mime = %s" if USE_POSTGRES else "image_mime = ?",
            "image_filename = %s" if USE_POSTGRES else "image_filename = ?",
        ]
        params += [image_bytes, image_mime, image_filename]
    else:
        if image_bytes is not None or image_mime is not None or image_filename is not None:
            sets += [
                "image_bytes = %s" if USE_POSTGRES else "image_bytes = ?",
                "image_mime = %s" if USE_POSTGRES else "image_mime = ?",
                "image_filename = %s" if USE_POSTGRES else "image_filename = ?",
            ]
            params += [image_bytes, image_mime, image_filename]

    if not sets:
        con.close()
        return

    params.append(recipe_id)
    sql = f"UPDATE recipes SET {', '.join(sets)} WHERE id = {'%s' if USE_POSTGRES else '?'}"
    cur.execute(sql, params)
    con.commit()
    con.close()


def delete_recipe(recipe_id: int) -> None:
    con = _connect()
    cur = con.cursor()
    cur.execute("DELETE FROM recipes WHERE id = %s" if USE_POSTGRES else "DELETE FROM recipes WHERE id = ?", (recipe_id,))
    con.commit()
    con.close()


def count_recipes() -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM recipes")
    n = cur.fetchone()["c"]
    con.close()
    return int(n)
