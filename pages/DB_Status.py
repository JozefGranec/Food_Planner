
# pages/DB Status.py
import streamlit as st
from food.db import init_db, get_backend_info, ping, count_recipes, self_test_write_read_delete

st.set_page_config(page_title="Database Status", page_icon="🩺", layout="centered")
st.title("🩺 Database Status")

# Initialize using the same logic as cookbook (Secrets first, else SQLite)
# If you used the auto-detect logic directly in cookbook.render(), you can call init_db() with no args here too.
try:
    init_db()  # cookbook already sets things up; this is safe/ idempotent
except TypeError:
    # If your cookbook passes kwargs (db_url/db_path), you can mirror that here if needed.
    init_db()

info = get_backend_info()
engine = info.get("engine")
dsn = info.get("dsn")
path = info.get("path")

def _mask_dsn(d):
    if not d or "://" not in d:
        return d
    # mask password: scheme://user:****@host:port/db?...
    try:
        scheme, rest = d.split("://", 1)
        if "@" in rest and ":" in rest.split("@")[0]:
            user, tail = rest.split("@", 1)[0], rest.split("@", 1)[1]
            user_name = user.split(":")[0]
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
        st.code(_mask_dsn(dsn), language="text")
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
st.subheader("Tips if you see SQLite on Streamlit Cloud")
st.markdown(
    """
- **You’re on SQLite:** The Streamlit Cloud filesystem is *ephemeral*. Your data will reset on restart/deploy.
- **Use Postgres via Secrets:** In **Settings → Secrets**, add something like:

```toml
[database]
url = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
