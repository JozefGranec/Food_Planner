# food/db.py
#T
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

_DB_PATH = Path("./food.sqlite3")

def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    """Create table if needed and ensure 'serves' column exists."""
    con = _connect()
    cur = con.cursor()
    # Create table (without worrying if it already exists)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            ingredients TEXT,
            instructions TEXT,
            image_bytes BLOB,
            image_mime TEXT,
            image_filename TEXT
            -- 'serves' may not exist yet in older DBs; we add it below if missing
        )
        """
    )
    # Ensure 'serves' column exists (SQLite has no easy IF NOT EXISTS for columns)
    cur.execute("PRAGMA table_info(recipes)")
    cols = [row["name"] for row in cur.fetchall()]
    if "serves" not in cols:
        cur.execute("ALTER TABLE recipes ADD COLUMN serves INTEGER")
    con.commit()
    con.close()

def add_recipe(
    title: str,
    ingredients: str = "",
    instructions: str = "",
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
    serves: Optional[int] = None,
) -> int:
    """Insert a recipe and return its new id."""
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO recipes
            (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves)
        VALUES
            (?, ?, ?, ?, ?, ?, ?)
        """,
        (title, ingredients, instructions, image_bytes, image_mime, image_filename, serves),
    )
    new_id = cur.lastrowid
    con.commit()
    con.close()
    return new_id

def list_recipes() -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, title, serves FROM recipes ORDER BY LOWER(title) ASC"
    )
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]

def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """
        SELECT
            id, title, ingredients, instructions,
            image_bytes, image_mime, image_filename, serves
        FROM recipes
        WHERE id = ?
        """,
        (recipe_id,),
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
    """
    Update fields that are not None. If keep_existing_image is True and
    no new image is provided, image fields are left untouched.
    """
    con = _connect()
    cur = con.cursor()

    sets = []
    params: List[Any] = []

    if title is not None:
        sets.append("title = ?")
        params.append(title)

    if ingredients is not None:
        sets.append("ingredients = ?")
        params.append(ingredients)

    if instructions is not None:
        sets.append("instructions = ?")
        params.append(instructions)

    if serves is not None:
        sets.append("serves = ?")
        params.append(serves)

    if not keep_existing_image:
        # We are replacing or clearing the image
        sets.append("image_bytes = ?")
        sets.append("image_mime = ?")
        sets.append("image_filename = ?")
        params.extend([image_bytes, image_mime, image_filename])
    else:
        # keep_existing_image=True: only update image if new bytes provided
        if image_bytes is not None or image_mime is not None or image_filename is not None:
            sets.append("image_bytes = ?")
            sets.append("image_mime = ?")
            sets.append("image_filename = ?")
            params.extend([image_bytes, image_mime, image_filename])

    if not sets:
        con.close()
        return  # nothing to update

    params.append(recipe_id)
    cur.execute(f"UPDATE recipes SET {', '.join(sets)} WHERE id = ?", params)
    con.commit()
    con.close()

def delete_recipe(recipe_id: int) -> None:
    con = _connect()
    cur = con.cursor()
    cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    con.commit()
    con.close()

def count_recipes() -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM recipes")
    n = cur.fetchone()["c"]
    con.close()
    return int(n)
