# services/db.py
import os
import streamlit as st
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine, Session

@st.cache_resource
def get_engine() -> Engine:
    # Prefer secrets; fallback to SQLite for dev.
    db_url = st.secrets.get("DATABASE_URL", None)
    if not db_url:
        db_url = "sqlite:///cookbook.db"
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, echo=False, connect_args=connect_args, pool_pre_ping=True)
    return engine

def get_session() -> Session:
    return Session(get_engine())

def create_db_and_tables():
    from models.recipe import Recipe, Ingredient  # import here to avoid circulars
    SQLModel.metadata.create_all(get_engine())
