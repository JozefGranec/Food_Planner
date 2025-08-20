# food/db.py
"""
DB helpers for Food Planner.
- Uses DATABASE_URL if present (Postgres on Neon/Supabase/Railway).
- Falls back to SQLite locally.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Any, List, Dict

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, Text, String, select,
    func, insert, update, delete
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
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

# For serverless/short‑lived environments, avoid persistent connection pooling
_engine: Engine = create_engine(DATABASE_URL, poolclass=NullPool, future=True)

metadata = MetaData()

recipes = Table(
    "recipes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(500), nullable=False),
    Column("ingredients", Text, nullable=True),
    Column("instructions", Text, nullable=True),
)

def init_db() -> None:
    """Create tables if they don't exist."""
    metadata.create_all(_engine)

def add_recipe(title: str, ingredients: str = "", instructions: str = "") -> int:
    if not title or not title.strip():
        raise ValueError("title is required")
    with _engine.begin() as conn:
        res = conn.execute(
            insert(recipes).values(
                title=title.strip(),
                ingredients=ingredients.strip(),
                instructions=instructions.strip(),
            )
        )
        # SQLite returns lastrowid; Postgres returns inserted_primary_key
        inserted_id = res.inserted_primary_key[0] if res.inserted_primary_key else None
        if inserted_id is None:
            # Try to fetch last id in a portable way
            row = conn.execute(
                select(func.max(recipes.c.id))
            ).scalar_one()
            return int(row)
        return int(inserted_id)

def list_recipes(search: Optional[str] = None) -> List[Dict[str, Any]]:
    with _engine.begin() as conn:
        if search and search.strip():
            s = select(recipes).where(
                func.lower(recipes.c.title).like(f"%{search.strip().lower()}%")
            ).order_by(func.lower(recipes.c.title))
        else:
            s = select(recipes).order_by(func.lower(recipes.c.title))
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
) -> None:
    values: Dict[str, Any] = {}
    if title is not None:
        values["title"] = title.strip()
    if ingredients is not None:
        values["ingredients"] = ingredients.strip()
    if instructions is not None:
        values["instructions"] = instructions.strip()
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
