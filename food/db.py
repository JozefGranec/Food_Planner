def init_db(*args, **kwargs) -> None:
    """
    Initialize the database connection.

    Priority:
      1) Explicit Postgres URL/parts passed via kwargs
      2) Streamlit Secrets: st.secrets["database"]
      3) SQLite fallback (food.sqlite3)
    """
    # 1) Explicit kwargs (Postgres)
    db_url = kwargs.get("db_url") or kwargs.get("url")
    if _looks_like_pg(db_url) or _looks_like_pg_parts(kwargs):
        _init_postgres(db_url, kwargs)
        _ensure_schema()
        return

    # 2) Try Streamlit Secrets → Postgres (if available)
    try:
        import streamlit as st  # local import so db.py works outside Streamlit too
        if "database" in st.secrets:
            db_secrets = dict(st.secrets["database"])
            url = db_secrets.get("url")
            if _looks_like_pg(url) or _looks_like_pg_parts(db_secrets):
                _init_postgres(url, db_secrets)
                _ensure_schema()
                return
    except Exception:
        # If secrets aren’t available (local run / tests), just continue
        pass

    # 3) SQLite fallback
    db_path = kwargs.get("db_path") or "food.sqlite3"
    _init_sqlite(db_path)
    _ensure_schema()
