# food/db.py
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import os
import streamlit as st

# --------------------------------------
# --- DATABASE CONFIGURATION ----------
# --------------------------------------

# Try to use Streamlit Secrets for PostgreSQL
POSTGRES_URL = None
if "database" in st.secrets:
    POSTGRES_URL = st.secrets["database"].get("url")

USE_POSTGRES = POSTGRES_URL is not None

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

    def _connect():
        con = psycopg2.connect(POSTGRES_URL)
        return con

else:
    # Local SQLite fallback
    _DB_PATH = Path("./food.sqlite3")

    def _connect():
        con = sqlite3.connect(_DB_PATH)
        con.row_factory = sqlite3.Row
        return con

# --------------------------------------
# --- DATABASE INITIALIZATION ----------
# --------------------------------------
def init_db() -> None:
    """Create recipes table if not exists."""
    con = _connect()
    cur = con.cursor()

    if USE_POSTGRES:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                ingredients TEXT,
                instructions TEXT,
                image_bytes BYTEA,
                image_mime TEXT,
                image_filename TEXT,
                serves INTEGER
            )
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT,
                instructions TEXT,
                image_bytes BLOB,
                image_mime TEXT,
                image_filename TEXT,
                serves INTEGER
            )
            """
        )
    con.commit()
    con.close()

# --------------------------------------
# --- CRUD OPERATIONS ------------------
# --------------------------------------
def add_recipe(
    title: str,
    ingredients: str = "",
    instructions: str = "",
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
    serves: Optional[int] = None,
) -> int:
    """Insert a recipe and return its ID."""
    con = _connect()
    cur = con.cursor()
    if USE_POSTGRES:
        cur.execute(
            """
            INSERT INTO recipes
                (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
        )
        new_id = cur.fetchone()[0]
    else:
        cur.execute(
            """
            INSERT INTO recipes
                (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
        )
        new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id


def list_recipes(limit: int = 200, search: Optional[str] = None) -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    if search:
        q = f"%{search.lower()}%"
        if USE_POSTGRES:
            cur.execute(
                "SELECT id, title, serves FROM recipes WHERE LOWER(title) LIKE %s ORDER BY title ASC LIMIT %s",
                (q, limit)
            )
        else:
            cur.execute(
                "SELECT id, title, serves FROM recipes WHERE LOWER(title) LIKE ? ORDER BY title ASC LIMIT ?",
                (q, limit)
            )
    else:
        if USE_POSTGRES:
            cur.execute("SELECT id, title, serves FROM recipes ORDER BY title ASC LIMIT %s", (limit,))
        else:
            cur.execute("SELECT id, title, serves FROM recipes ORDER BY title ASC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()

    result = []
    for r in rows:
        if USE_POSTGRES:
            result.append(dict(r))
        else:
            result.append(dict(r))
    return result


def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    if USE_POSTGRES:
        cur.execute(
            """
            SELECT id, title, ingredients, instructions, image_bytes, image_mime, image_filename, serves
            FROM recipes WHERE id = %s
            """,
            (recipe_id,)
        )
    else:
        cur.execute(
            """
            SELECT id, title, ingredients, instructions, image_bytes, image_mime, image_filename, serves
            FROM recipes WHERE id = ?
            """,
            (recipe_id,)
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
    params = []

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
    if not keep_existing_image or image_bytes is not None:
        sets.append("image_bytes = %s" if USE_POSTGRES else "image_bytes = ?")
        sets.append("image_mime = %s" if USE_POSTGRES else "image_mime = ?")
        sets.append("image_filename = %s" if USE_POSTGRES else "image_filename = ?")
        params.extend([image_bytes, image_mime, image_filename])

    if not sets:
        con.close()
        return  # nothing to update

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
    cur.execute("SELECT COUNT(*) AS c")
    n = cur.fetchone()[0]
    con.close()
    return int(n)
