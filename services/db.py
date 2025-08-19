# services/db.py
import streamlit as st
import os
import sqlite3
import tempfile
import shutil

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

DB_FILE = "./cookbook.db"  # same file used in DB_URL ("sqlite:///./cookbook.db")

def get_db_path() -> str:
    return DB_FILE

def export_db_bytes() -> bytes:
    """
    Create a consistent snapshot of the SQLite file and return its bytes.
    Uses the SQLite backup API to avoid partial copies while the app is running.
    """
    src_path = get_db_path()
    # ensure file exists (tables are created at startup)
    if not os.path.exists(src_path):
        # create empty db so the download isn't missing
        create_db_and_tables()

    # create a temp backup file via SQLite backup API
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with sqlite3.connect(src_path) as src, sqlite3.connect(tmp_path) as dst:
            src.backup(dst)  # consistent snapshot
        with open(tmp_path, "rb") as f:
            data = f.read()
        return data
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

def restore_db_bytes(data: bytes) -> bool:
    """
    Replace the current cookbook.db with the uploaded bytes.
    We dispose the SQLAlchemy engine so no handles are open, then overwrite the file,
    and finally clear the cached engine so Streamlit re-creates it on next use.
    """
    # 1) dispose existing engine/handles
    eng = get_engine()
    eng.dispose()
    try:
        get_engine.clear()  # clear the @st.cache_resource so a fresh engine is created
    except Exception:
        pass

    # 2) write uploaded bytes to a temp file, then atomically copy over the DB file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        tmp_path = tmp.name

    try:
        shutil.copyfile(tmp_path, get_db_path())
        return True
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
