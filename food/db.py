# ---------- Diagnostics ----------
def get_backend_info() -> dict:
    """Public: see which backend is active and basic connection info."""
    return {
        "engine": _engine(),      # "sqlite" | "postgres"
        "dsn": _DB.get("dsn"),    # Postgres DSN if used (mask in UI!)
        "path": _DB.get("path"),  # SQLite path if used
    }

def ping() -> bool:
    """Return True if a simple SELECT works, else False."""
    try:
        con = _conn()
        cur = con.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        return False

def self_test_write_read_delete() -> dict:
    """
    Try writing a throwaway recipe, reading it back, then deleting it.
    Returns {'ok': bool, 'id': int|None, 'error': str|None}
    """
    try:
        new_id = add_recipe(title="__db_self_test__", ingredients="", instructions="", serves=1)
        got = get_recipe(new_id)
        delete_recipe(new_id)
        return {"ok": bool(got and got.get("id") == new_id), "id": new_id, "error": None}
    except Exception as e:
        return {"ok": False, "id": None, "error": str(e)}
