# pages/DB_Status.py
import socket
import urllib.parse
from typing import Optional

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

# -------------------------------
# Helpers
# -------------------------------
def mask_url(url: Optional[str]) -> Optional[str]:
    """Mask password in a DSN/URL, keep everything else visible."""
    if not url or "://" not in url:
        return url
    try:
        p = urllib.parse.urlsplit(url)
        if p.username:
            netloc = f"{p.username}:****@{p.hostname or ''}{(':'+str(p.port)) if p.port else ''}"
            return urllib.parse.urlunsplit((p.scheme, netloc, p.path, p.query, p.fragment))
    except Exception:
        pass
    return url

def mask_dsn(dsn: Optional[str]) -> Optional[str]:
    # Reuse mask_url (works for postgres URLs too)
    return mask_url(dsn)

def tcp_probe(host: str, port: int, timeout: float = 5.0) -> None:
    """Try a plain TCP connection; raise with a helpful message on failure."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return
    except socket.gaierror:
        st.error("❌ Host name not found (DNS). Check the `host` value in your Secrets.")
        st.stop()
    except TimeoutError:
        st.error(
            "❌ Connection timed out. This often means a firewall or IP allowlist is blocking Streamlit Cloud.\n\n"
            "- Ensure your database allows public access, or\n"
            "- Add Streamlit Cloud egress IPs to your allowlist (varies by provider)."
        )
        st.stop()
    except ConnectionRefusedError:
        st.error("❌ Connection refused. Wrong port or the server isn’t listening.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Could not reach {host}:{port} — {type(e).__name__}: {e}")
        st.stop()

# -------------------------------
# Read Secrets & PRE-CHECK reachability (before init_db)
# -------------------------------
_db = dict(st.secrets.get("database", {}))
host: Optional[str] = None
port: Optional[int] = None

if _db.get("url"):  # DSN string present
    st.caption("Using Postgres URL from Secrets.")
    try:
        p = urllib.parse.urlsplit(_db["url"])
        host = p.hostname
        port = p.port or 5432
        st.caption(f"Parsed from URL → host={host}, port={port}")
    except Exception:
        st.error(f"Could not parse DB URL. Check Secrets.\nURL (masked): {mask_url(_db['url'])}")
        st.stop()
elif _db:
    st.caption("Using Postgres parts from Secrets.")
    host = _db.get("host")
    port = int(_db.get("port", 5432))
    st.caption(f"Using parts → host={host}, port={port}")
else:
    st.info("No `[database]` in Secrets. Falling back to local SQLite (useful for local dev).")

# If we appear to be using Postgres, probe TCP first to give clearer errors
if host and port:
    st.write("Probing TCP reachability…")
    tcp_probe(host, port)
    st.success(f"TCP reachability OK: {host}:{port}")

# -------------------------------
# Initialize DB (with friendly error)
# -------------------------------
try:
    if _db.get("url"):
        init_db(db_url=_db["url"])
    elif _db:
        init_db(**_db)
    else:
        init_db()  # SQLite fallback
except Exception as e:
    m = mask_url(_db.get("url"))
    st.error(
        "Postgres connection failed. Check Secrets (URL/parts), password encoding, network/SSL.\n\n"
        f"URL (masked): {m or '(using parts)'}\n\n"
        f"Error: {type(e).__name__}: {e}"
    )
    st.stop()

# -------------------------------
# Display backend info & health
# -------------------------------
info = get_backend_info()
engine = info.get("engine")
dsn = info.get("dsn")
path = info.get("path")

st.subheader("Backend")
c1, c2 = st.columns(2)
with c1:
    st.metric("Engine", engine or "unknown")
with c2:
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
st.subheader("Tips")
st.markdown(
    "- **If it still shows SQLite on Streamlit Cloud**: your Secrets weren’t read or the PG connection failed.\n"
    "- **Prefer parts in Secrets** to avoid URL-encoding password issues:\n"
)
st.code(
    '[database]\n'
    'user = "ACTUAL_USER"\n'
    'password = "ACTUAL_PASSWORD"\n'
    'host = "ACTUAL_HOST"\n'
    'port = 5432\n'
    'dbname = "ACTUAL_DBNAME"\n'
    'sslmode = "require"\n',
    language="toml",
)
