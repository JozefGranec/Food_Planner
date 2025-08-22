# pages/DB_Status.py
import streamlit as st
from food.db import (
    init_db,
    get_backend_info,
    ping,
    count_recipes,
    self_test_write_read_delete,
)

st.set_page_config(page_title="Database Status", page_icon="🩺", layout="centered")
st.title("🩺 Database Status")

# --- Initialize DB explicitly from Secrets (Postgres) or fallback to SQLite ---
_db = dict(st.secrets.get("database", {}))
if _db.get("url"):           # preferred: single DSN in secrets
    init_db(db_url=_db["url"])
elif _db:                    # parts: user/password/host/port/dbname/sslmode
    init_db(**_db)
else:                        # local dev fallback
    init_db()

info = get_backend_info()
engine = info.get("engine")
dsn = info.get("dsn")
path = info.get("path")

def mask_dsn(d: str | None) -> str | None:
    if not d or "://" not in d:
        return d
    try:
        scheme, rest = d.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            user_part, tail = rest.split("@", 1)
            user_name = user_part.split(":", 1)[0]
            return f"{scheme}://{user_name}:****@{tail}"
        return d
    except Exception:
        return d

st.subheader("Backend")
col1, col2 = st.columns(2)
with col1:
    st.metric("Engine", engine or "unknown")
with col2:
    if engine == "postgres":
        st.code(mask_dsn(dsn) or "(no DSN)", language="text")
    elif engine == "sqlite":
        st.code(path or "(in-memory?)", language="text")
    else:
        st.code("(no connection)", language="text")

st.subheader("Health checks")
ok_ping = ping()
st.write(f"**Ping:** {'✅ OK' if ok_ping else '❌ Failed'}")

try:
    total = count_recipes()
    st.write(f"**Count:** {total} recipes")
except Exception as e:
    st.error(f"Counting failed: {e}")

if st.button("Run write/read/delete self-test"):
    res = self_test_write_read_delete()
    if res["ok"]:
        st.success(f"Self-test passed (test id {res['id']}).")
    else:
        st.error(f"Self-test failed: {res['error']}")

st.divider()
st.subheader("Using Postgres on Streamlit Cloud")
st.markdown(
    "- Add to requirements.txt: `streamlit`, `pillow`, `psycopg2-binary`.\n"
    "- In Settings → Secrets, set:\n"
)
st.code(
    '[database]\n'
    'url = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"\n',
    language="toml",
)
