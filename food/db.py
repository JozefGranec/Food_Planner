# food/db.py
"""
DB helpers for Food Planner.
- Uses DATABASE_URL if present (Postgres on Neon/Supabase/Railway).
- Falls back to SQLite locally.
- Supports optional recipe images stored as BLOB/BYTEA.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Any, List, Dict

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, Text, String, LargeBinary,
    select, func, insert, update, delete, text, inspect
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

# Try to read secrets from Streamlit if available
def _get_database_url() -> Optional[str]:
    # 1) Streamlit secrets
    try:
        import streamlit as st  # type: ignore
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    # 2) Environment
    return os.getenv("DATABASE_URL")

# Fallback SQLite (local dev)
LOCAL_SQLITE = Path.home() / ".food_planner" / "recipes.db"
LOCAL_SQLITE.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = _get_database_url() or f"sqlite:///{LOCAL_SQLITE}"

# For serverless/short-lived environments, avoid persistent connection pooling
_engine: Engine = create_engine(DATABASE_URL, poolclass=NullPool, future=True)

metadata = MetaData()

recipes = Table(
    "recipes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(500), nullable=False),
    Column("ingredients", Text, nullable=True),
    Column("instructions", Text, nullable=True),
    # New image fields (created on fresh DBs; added via migration if existing)
    Column("image_bytes", LargeBinary, nullable=True),
    Column("image_mime", String(255), nullable=True),
    Column("image_filename", String(500), nullable=True),
)

def _ensure_image_columns() -> None:
    """Lightweight in-place migration: add image columns if they are missing."""
    insp = inspect(_engine)
    if not insp.has_table("recipes"):
        return
    cols = {c["name"] for c in insp.get_columns("recipes")}
    if {"image_bytes", "image_mime", "image_filename"} <= cols:
        return

    dialect = _engine.dialect.name  # 'sqlite', 'postgresql', etc.
    with _engine.begin() as conn:
        if "image_bytes" not in cols:
            if dialect == "postgresql":
                conn.execute(text("ALTER TABLE recipes ADD COLUMN image_bytes BYTEA"))
            else:
                # sqlite / others
                conn.execute(text("ALTER TABLE recipes ADD COLUMN image_bytes BLOB"))
        if "image_mime" not in cols:
            if dialect == "postgresql":
                conn.execute(text("ALTER TABLE recipes ADD COLUMN image_mime TEXT"))
            else:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN image_mime TEXT"))
        if "image_filename" not in cols:
            if dialect == "postgresql":
                conn.execute(text("ALTER TABLE recipes ADD COLUMN image_filename TEXT"))
            else:
                conn.execute(text("ALTER TABLE recipes ADD COLUMN image_filename TEXT"))

def init_db() -> None:
    """Create tables if they don't exist and ensure new columns exist."""
    metadata.create_all(_engine)  # creates full schema on new DBs
    _ensure_image_columns()       # adds missing columns on existing DBs

def add_recipe(
    title: str,
    ingredients: str = "",
    instructions: str = "",
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
    image_filename: Optional[str] = None,
) -> int:
    if not title or not title.strip():
        raise ValueError("title is required")
    with _engine.begin() as conn:
        res = conn.execute(
            insert(recipes).values(
                title=title.strip(),
                ingredients=ingredients.strip(),
                instructions=instructions.strip(),
                image_bytes=image_bytes,
                image_mime=(image_mime or None),
                image_filename=(image_filename or None),
            )
        )
        inserted_id = res.inserted_primary_key[0] if res.inserted_primary_key else None
        if inserted_id is None:
            row = conn.execute(select(func.max(recipes.c.id))).scalar_one()
            return int(row)
        return int(inserted_id)

def list_recipes(search: Optional[str] = None) -> List[Dict[str, Any]]:
    with _engine.begin() as conn:
        if search and search.strip():
            s = (
                select(
                    recipes.c.id,
                    recipes.c.title,
                    # lightweight "has_image" flag if you ever need it in UI
                    (recipes.c.image_bytes.isnot(None)).label("has_image")
                )
                .where(func.lower(recipes.c.title).like(f"%{search.strip().lower()}%"))
                .order_by(func.lower(recipes.c.title))
            )
        else:
            s = (
                select(
                    recipes.c.id,
                    recipes.c.title,
                    (recipes.c.image_bytes.isnot(None)).label("has_image")
                )
                .order_by(func.lower(recipes.c.title))
            )
        rows = conn.execute(s).mappings().all()
        return [dict(r) for r in rows]

def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    with _engine.begin() as conn:
        row = conn.execute(
            select(recipes).where(recipes.c.id == recipe_id)
        ).mappings().first()
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
) -> None:
    values: Dict[str, Any] = {}
    if title is not None:
        values["title"] = title.strip()
    if ingredients is not None:
        values["ingredients"] = ingredients.strip()
    if instructions is not None:
        values["instructions"] = instructions.strip()

    # Replace image only if caller provided new bytes and does NOT want to keep old
    if not keep_existing_image and image_bytes is not None:
        values["image_bytes"] = image_bytes
        values["image_mime"] = image_mime or None
        values["image_filename"] = image_filename or None

    if not values:
        return
    with _engine.begin() as conn:
        conn.execute(update(recipes).where(recipes.c.id == recipe_id).values(**values))

def delete_recipe(recipe_id: int) -> None:
    with _engine.begin() as conn:
        conn.execute(delete(recipes).where(recipes.c.id == recipe_id))

def count_recipes() -> int:
    with _engine.begin() as conn:
        return int(conn.execute(select(func.count()).select_from(recipes)).scalar_one())
