# services/db.py
import streamlit as st
from sqlalchemy.engine import Engine
from sqlalchemy import event, text
from sqlmodel import SQLModel, create_engine, Session

DB_URL = "sqlite:///./cookbook.db"

@st.cache_resource
def get_engine() -> Engine:
    engine = create_engine(
        DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},  # required for SQLite with Streamlit threads
        pool_pre_ping=True,
    )

    # Apply SQLite pragmas for performance and reliability
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    return engine

def get_session() -> Session:
    return Session(get_engine())

def create_db_and_tables():
    # Import models here to avoid circular imports
    from models.recipe import Recipe, Ingredient
    SQLModel.metadata.create_all(get_engine())

def vacuum():
    # Optional maintenance; call rarely
    with get_session() as s:
        s.exec(text("VACUUM"))
