# food/db.py
from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, List, Optional

# Optional: Postgres driver. If missing, we'll fall back to SQLite unless PG is explicitly requested.
try:
    import psycopg2  # type: ignore
except Exception:
    psycopg2 = None  # type: ignore

# In-memory state
_DB: Dict[str, Any] = {"engine": None, "conn": None, "dsn": None, "path": None}


# ---------- Public API ----------
def init_db(*args, **kwargs) -> None:
    """
    Initialize the database connection.

    Priority:
      1) Explicit Postgres URL/parts passed via kwargs
      2) Streamlit Secrets: st.secrets["database"] (URL or parts)
      3) SQLite fallback: food.sqlite3
    """
    # 1) Explicit kwargs → Postgres if URL/parts present
    db_url = kwargs.get("db_url") or kwargs.get("url")
    if _looks_like_pg(db_url) or _looks_like_pg_parts(kwargs):
        _init_postgres(db_url, kwargs)
        _ensure_schema()
        return

    # 2) Try Streamlit Secrets (safe even when not running under Streamlit)
    try:
        import streamlit as st  # local import so importing db.py never depends on Streamlit
        if "database" in st.secrets:
            db_secrets = dict(st.secrets["database"])
            url = db_secrets.get("url")
            if _looks_like_pg(url) or _looks_like_pg_parts(db_secrets):
                _init_postgres(url, db_secrets)
                _ensure_schema()
                return
    except Exception:
        # Not in Streamlit or no secrets; continue to SQLite
        pass

    # 3) SQLite fallback
    db_path = kwargs.get("db_path") or "food.sqlite3"
    _init_sqlite(db_path)
    _ensure_schema()


def add_recipe(
    *,
    title: str,
    ingredients: Optional[str] = None,
    instructions: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
    serves: Optional[int] = None,
    servings: Optional[int] = None,  # compatibility
) -> int:
    """Insert a recipe and return the new id."""
    con = _conn()
    cur = con.cursor()
    eng = _engine()
    s = _to_int(serves if serves is not None else servings, 0)

    if eng == "postgres":
        cur.execute(
            """
            INSERT INTO recipes
              (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves, updated_at)
            VALUES
              (%s,    %s,          %s,           %s,          %s,         %s,             %s,     NOW())
            RETURNING id;
            """,
            (title.strip(), ingredients or "", instructions or "",
             _pg_bin(image_bytes), image_mime, image_filename, s),
        )
        new_id = cur.fetchone()[0]
    else:
        cur.execute(
            """
            INSERT INTO recipes
              (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves, updated_at)
            VALUES
              (?,     ?,           ?,            ?,           ?,          ?,              ?,      ?)
            """,
            (title.strip(), ingredients or "", instructions or "",
             image_bytes, image_mime, image_filename, s, sqlite3_datetime_now()),
        )
        new_id = cur.lastrowid

    con.commit()
    cur.close()
    return int(new_id)


def list_recipes() -> List[Dict[str, Any]]:
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT id, title FROM recipes ORDER BY title ASC;")
    rows = cur.fetchall()
    cur.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({"id": r["id"], "title": r["title"]} if isinstance(r, sqlite3.Row) else {"id": r[0], "title": r[1]})
    return out


def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    con = _conn()
    cur = con.cursor()
    if _engine() == "postgres":
        cur.execute(
            """
            SELECT id, title, ingredients, instructions, image_bytes, image_mime,
                   image_filename, serves, created_at, updated_at
            FROM recipes WHERE id = %s;
            """,
            (recipe_id,),
        )
    else:
        cur.execute(
            """
            SELECT id, title, ingredients, instructions, image_bytes, image_mime,
                   image_filename, serves, created_at, updated_at
            FROM recipes WHERE id = ?;
            """,
