# food/db.py
"""
Database layer for the Cook Book.

Features
--------
- Works with local SQLite (default: food.sqlite3)
- Works with PostgreSQL when a DSN/parts are provided (e.g., via Streamlit Secrets)
- Uniform functions:
    init_db(...)
    add_recipe(...)
    list_recipes()
    get_recipe(id)
    update_recipe(...)
    delete_recipe(id)
    count_recipes()

Notes
-----
- 'serves' is the canonical field. We also accept/emit 'servings' for compatibility.
- Images are stored as bytes (BLOB in SQLite, BYTEA in Postgres).
- add_recipe returns the new integer ID.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

# Optional import: psycopg2 might not be installed locally.
try:
    import psycopg2
    import psycopg2.extras
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore

# -----------------------
# Globals / simple state
# -----------------------
_DB: Dict[str, Any] = {
    "engine": None,     # "sqlite" | "postgres"
    "conn": None,       # connection object
    "dsn": None,        # for postgres (if used)
    "path": None,       # for sqlite (if used)
}

# -----------------------
# Init / Connection
# -----------------------
def init_db(*args, **kwargs) -> None:
    """
    Initialize the database connection.

    Accepted inputs (kwargs):
      - db_url / url : full DSN (e.g., postgresql+psycopg2://USER:PASS@HOST:5432/DB?sslmode=require)
                       or plain "postgresql://..." accepted by psycopg2
      - db_path      : path to SQLite file (default: 'food.sqlite3')
      - Or discrete parts via **kwargs: user, password, host, port, dbname/database, sslmode

    Logic:
      1) If a Postgres URL/parts are provided, try Postgres
      2) Else fallback to SQLite at db_path or default file
    """
    # 1) Try Postgres if we detect URL or parts that imply PG
    db_url = kwargs.get("db_url") or kwargs.get("url")
    if _looks_like_pg(db_url) or _looks_like_pg_parts(kwargs):
        _init_postgres(db_url, kwargs)
        _ensure_schema()
        return

    # 2) SQLite fallback
    db_path = kwargs.get("db_path") or "food.sqlite3"
    _init_sqlite(db_path)
    _ensure_schema()


def _looks_like_pg(url: Optional[str]) -> bool:
    if not url:
        return False
    u = url.lower()
    return "postgres" in u  # accepts postgresql:// or postgresql+psycopg2:// etc.


def _looks_like_pg_parts(parts: Dict[str, Any]) -> bool:
    keys = set(k.lower() for k in parts.keys())
    return any(k in keys for k in ("user", "username", "password", "host", "port", "dbname", "database"))


def _build_pg_dsn(url: Optional[str], parts: Dict[str, Any]) -> Optional[str]:
    if url:
        return url  # Let psycopg2 parse it

    user = parts.get("user") or parts.get("username")
    pwd = parts.get("password")
    host = parts.get("host", "localhost")
    port = parts.get("port", 5432)
    dbname = parts.get("dbname") or parts.get("database")
    sslmode = parts.get("sslmode")

    if not (user and pwd and dbname):
        return None

    dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"
    if sslmode:
        joiner = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{joiner}sslmode={sslmode}"
    return dsn


def _init_postgres(url: Optional[str], parts: Dict[str, Any]) -> None:
    if psycopg2 is None:
        raise RuntimeError(
            "psycopg2 is not installed. Install it or disable Postgres usage. "
            "On Streamlit Cloud, add psycopg2-binary to your requirements.txt."
        )

    dsn = _build_pg_dsn(url, parts)
    if not dsn:
        # If we ended here, caller hinted PG but didn't provide usable creds → fall back to SQLite
        _init_sqlite(parts.get("db_path") or "food.sqlite3")
        return

    conn = psycopg2.connect(dsn)
    conn.autocommit = False  # We'll control commits
    _DB.update({
        "engine": "postgres",
        "conn": conn,
        "dsn": dsn,
        "path": None,
    })


def _init_sqlite(path: str) -> None:
    # Ensure containing folder exists
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _DB.update({
        "engine": "sqlite",
        "conn": conn,
        "dsn": None,
        "path": path,
    })


def _conn():
    if not _DB.get("conn"):
        # Default to local SQLite if init_db was never called
        _init_sqlite("food.sqlite3")
        _ensure_schema()
    return _DB["conn"]


def _engine() -> str:
    return _DB.get("engine") or "sqlite"


# -----------------------
# Schema creation
# -----------------------
def _ensure_schema() -> None:
    eng = _engine()
    con = _conn()
    cur = con.cursor()

    if eng == "postgres":
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id           SERIAL PRIMARY KEY,
                title        TEXT NOT NULL,
                ingredients  TEXT,
                instructions TEXT,
                image_bytes  BYTEA,
                image_mime   TEXT,
                image_filename TEXT,
                serves       INTEGER DEFAULT 0,
                created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
        # No trigger; we update updated_at from the app on writes
    else:  # sqlite
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                title          TEXT NOT NULL,
                ingredients    TEXT,
                instructions   TEXT,
                image_bytes    BLOB,
                image_mime     TEXT,
                image_filename TEXT,
                serves         INTEGER DEFAULT 0,
                created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    con.commit()
    cur.close()


# -----------------------
# Helpers
# -----------------------
def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _pg_binary(data: Optional[bytes]) -> Optional[Any]:
    if data is None:
        return None
    if psycopg2 is None:
        return data
    return psycopg2.Binary(data)


def _placeholders(n: int) -> str:
    """Return placeholders string depending on engine."""
    if _engine() == "postgres":
        return "(" + ",".join(["%s"] * n) + ")"
    return "(" + ",".join(["?"] * n) + ")"


# -----------------------
# CRUD API
# -----------------------
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
    """
    Insert a recipe and return the new id.
    Accepts 'serves' or 'servings' (serves wins if both given).
    """
    con = _conn()
    cur = con.cursor()
    eng = _engine()

    serves_val = _to_int(serves if serves is not None else servings, 0)

    cols = [
        "title", "ingredients", "instructions",
        "image_bytes", "image_mime", "image_filename",
        "serves", "updated_at"
    ]
    ph = _placeholders(len(cols))

    if eng == "postgres":
        sql = f"""
            INSERT INTO recipes {tuple(cols)} VALUES {ph}
            RETURNING id;
        """
        params = (
            title.strip(),
            ingredients or "",
            instructions or "",
            _pg_binary(image_bytes),
            image_mime,
            image_filename,
            serves_val,
            # updated_at
            psycopg2.extras.Json(None) if False else None  # placeholder, will set via NOW()
        )
        # Replace last param with NOW() by using SQL literal
        sql = sql.replace("%s)", "NOW())")  # only for the last placeholder
        cur.execute(sql, params[:-1])       # pass all except the NOW() placeholder
        new_id = cur.fetchone()[0]
    else:
        sql = f"""
            INSERT INTO recipes {tuple(cols)} VALUES {ph}
        """
        params = (
            title.strip(),
            ingredients or "",
            instructions or "",
            image_bytes,
            image_mime,
            image_filename,
            serves_val,
            # updated_at
            sqlite3_datetime_now(),
        )
        cur.execute(sql, params)
        new_id = cur.lastrowid

    con.commit()
    cur.close()
    return int(new_id)


def list_recipes() -> List[Dict[str, Any]]:
    """
    Return a list of recipes with minimal fields used in the list view.
    Each item: {"id": int, "title": str}
    """
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT id, title FROM recipes ORDER BY title ASC;")
    rows = cur.fetchall()
    cur.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, sqlite3.Row):
            out.append({"id": r["id"], "title": r["title"]})
        else:
            out.append({"id": r[0], "title": r[1]})
    return out


def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    """
    Return a single recipe as a dict with all fields or None if not found.
    """
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, title, ingredients, instructions,
               image_bytes, image_mime, image_filename,
               serves, created_at, updated_at
        FROM recipes
        WHERE id = %s;
        """ if _engine() == "postgres" else
        """
        SELECT id, title, ingredients, instructions,
               image_bytes, image_mime, image_filename,
               serves, created_at, updated_at
        FROM recipes
        WHERE id = ?;
        """,
        (recipe_id,)
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None

    if isinstance(row, sqlite3.Row):
        d = dict(row)
    else:
        # psycopg2 returns tuples by default
        d = {
            "id": row[0],
            "title": row[1],
            "ingredients": row[2],
            "instructions": row[3],
            "image_bytes": row[4],
            "image_mime": row[5],
            "image_filename": row[6],
            "serves": row[7],
            "created_at": row[8],
            "updated_at": row[9],
        }

    # Back-compat: readers might look for 'servings'
    if "servings" not in d:
        d["servings"] = d.get("serves", 0)
    return d


def update_recipe(
    *,
    recipe_id: int,
    title: Optional[str] = None,
    ingredients: Optional[str] = None,
    instructions: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
    keep_existing_image: bool = True,
    serves: Optional[int] = None,
    servings: Optional[int] = None,  # compatibility
) -> None:
    """
    Update fields of a recipe.
    - If keep_existing_image is True and image_* are None, the image is left untouched.
    - If keep_existing_image is False and all image_* are None, the image is cleared.
    """
    con = _conn()
    cur = con.cursor()
    eng = _engine()

    sets: List[str] = []
    params: List[Any] = []

    if title is not None:
        sets.append("title = %s" if eng == "postgres" else "title = ?")
        params.append(title.strip())

    if ingredients is not None:
        sets.append("ingredients = %s" if eng == "postgres" else "ingredients = ?")
        params.append(ingredients)

    if instructions is not None:
        sets.append("instructions = %s" if eng == "postgres" else "instructions = ?")
        params.append(instructions)

    # serves/servings
    target_serves = serves if serves is not None else servings
    if target_serves is not None:
        sets.append("serves = %s" if eng == "postgres" else "serves = ?")
        params.append(_to_int(target_serves, 0))

    # image handling
    if keep_existing_image:
        if image_bytes is not None:
            sets.append("image_bytes = %s" if eng == "postgres" else "image_bytes = ?")
            params.append(_pg_binary(image_bytes) if eng == "postgres" else image_bytes)
        if image_mime is not None:
            sets.append("image_mime = %s" if eng == "postgres" else "image_mime = ?")
            params.append(image_mime)
        if image_filename is not None:
            sets.append("image_filename = %s" if eng == "postgres" else "image_filename = ?")
            params.append(image_filename)
    else:
        # Explicitly clear unless new values are provided
        sets.append("image_bytes = %s" if eng == "postgres" else "image_bytes = ?")
        sets.append("image_mime = %s" if eng == "postgres" else "image_mime = ?")
        sets.append("image_filename = %s" if eng == "postgres" else "image_filename = ?")
        params.extend([
            _pg_binary(image_bytes) if (eng == "postgres" and image_bytes is not None) else image_bytes,
            image_mime,
            image_filename
        ])

    # updated_at
    if eng == "postgres":
        sets.append("updated_at = NOW()")
    else:
        sets.append("updated_at = ?")
        params.append(sqlite3_datetime_now())

    # WHERE
    params.append(recipe_id)

    sql = f"""
        UPDATE recipes
        SET {", ".join(sets)}
        WHERE id = %s;
    """ if eng == "postgres" else f"""
        UPDATE recipes
        SET {", ".join(sets)}
        WHERE id = ?;
    """

    cur.execute(sql, tuple(params))
    con.commit()
    cur.close()


def delete_recipe(recipe_id: int) -> None:
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "DELETE FROM recipes WHERE id = %s;" if _engine() == "postgres" else "DELETE FROM recipes WHERE id = ?;",
        (recipe_id,)
    )
    con.commit()
    cur.close()


def count_recipes() -> int:
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM recipes;")
    row = cur.fetchone()
    cur.close()
    if not row:
        return 0
    # sqlite returns tuple or Row; psycopg2 returns tuple
    return int(row[0])


# -----------------------
# SQLite time helper
# -----------------------
def sqlite3_datetime_now() -> str:
    """
    Return a SQLite-friendly current timestamp string.
    Using application-side timestamp for portability.
    """
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
