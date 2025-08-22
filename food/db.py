# food/db.py
from __future__ import annotations
import os, sqlite3
from typing import Any, Dict, List, Optional

# Optional: only used for Postgres
try:
    import psycopg2, psycopg2.extras
except Exception:
    psycopg2 = None  # type: ignore

_DB: Dict[str, Any] = {"engine": None, "conn": None, "dsn": None, "path": None}

def init_db(*args, **kwargs) -> None:
    """
    Initialize DB.
    Accepts:
      - db_url / url (postgres DSN)
      - db_path (sqlite file path)
      - or parts: user,password,host,port,dbname/database,sslmode
    If no usable Postgres info → falls back to SQLite 'food.sqlite3'.
    """
    db_url = kwargs.get("db_url") or kwargs.get("url")
    if _looks_like_pg(db_url) or _looks_like_pg_parts(kwargs):
        _init_postgres(db_url, kwargs)
        _ensure_schema()
        return
    _init_sqlite(kwargs.get("db_path") or "food.sqlite3")
    _ensure_schema()

def _looks_like_pg(url: Optional[str]) -> bool:
    return bool(url and "postgres" in url.lower())

def _looks_like_pg_parts(parts: Dict[str, Any]) -> bool:
    ks = {k.lower() for k in parts.keys()}
    return any(k in ks for k in ("user","username","password","host","port","dbname","database"))

def _build_pg_dsn(url: Optional[str], parts: Dict[str, Any]) -> Optional[str]:
    if url: return url
    user = parts.get("user") or parts.get("username")
    pwd  = parts.get("password")
    host = parts.get("host","localhost")
    port = parts.get("port",5432)
    dbn  = parts.get("dbname") or parts.get("database")
    ssl  = parts.get("sslmode")
    if not (user and pwd and dbn): return None
    dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{dbn}"
    if ssl: dsn += f"?sslmode={ssl}"
    return dsn

def _init_postgres(url: Optional[str], parts: Dict[str, Any]) -> None:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed. Add 'psycopg2-binary' to requirements.txt.")
    dsn = _build_pg_dsn(url, parts)
    if not dsn:
        _init_sqlite(parts.get("db_path") or "food.sqlite3"); return
    conn = psycopg2.connect(dsn); conn.autocommit = False
    _DB.update({"engine":"postgres","conn":conn,"dsn":dsn,"path":None})

def _init_sqlite(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
    _DB.update({"engine":"sqlite","conn":conn,"dsn":None,"path":path})

def _conn():
    if not _DB.get("conn"):
        _init_sqlite("food.sqlite3"); _ensure_schema()
    return _DB["conn"]

def _engine() -> str:
    return _DB.get("engine") or "sqlite"

def _ensure_schema() -> None:
    con = _conn(); cur = con.cursor()
    if _engine() == "postgres":
        cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
          id SERIAL PRIMARY KEY,
          title TEXT NOT NULL,
          ingredients TEXT,
          instructions TEXT,
          image_bytes BYTEA,
          image_mime TEXT,
          image_filename TEXT,
          serves INTEGER DEFAULT 0,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          ingredients TEXT,
          instructions TEXT,
          image_bytes BLOB,
          image_mime TEXT,
          image_filename TEXT,
          serves INTEGER DEFAULT 0,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );""")
    con.commit(); cur.close()

def _to_int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return default

def _pg_bin(b: Optional[bytes]):
    return None if b is None else (psycopg2.Binary(b) if psycopg2 else b)

def sqlite3_datetime_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# ---------- CRUD ----------
def add_recipe(*, title: str, ingredients: Optional[str]=None, instructions: Optional[str]=None,
               image_bytes: Optional[bytes]=None, image_mime: Optional[str]=None,
               image_filename: Optional[str]=None, serves: Optional[int]=None,
               servings: Optional[int]=None) -> int:
    con=_conn(); cur=con.cursor(); eng=_engine()
    s=_to_int(serves if serves is not None else servings,0)
    cols=("title","ingredients","instructions","image_bytes","image_mime","image_filename","serves","updated_at")
    if eng=="postgres":
        sql=f"INSERT INTO recipes {cols} VALUES (%s,%s,%s,%s,%s,%s,%s,NOW()) RETURNING id;"
        cur.execute(sql,(title.strip(), ingredients or "", instructions or "",
                         _pg_bin(image_bytes), image_mime, image_filename, s))
        new_id=cur.fetchone()[0]
    else:
        sql=f"INSERT INTO recipes {cols} VALUES (?,?,?,?,?,?,?,?)"
        cur.execute(sql,(title.strip(), ingredients or "", instructions or "",
                         image_bytes, image_mime, image_filename, s, sqlite3_datetime_now()))
        new_id=cur.lastrowid
    con.commit(); cur.close(); return int(new_id)

def list_recipes() -> List[Dict[str,Any]]:
    con=_conn(); cur=con.cursor()
    cur.execute("SELECT id, title FROM recipes ORDER BY title ASC;")
    rows=cur.fetchall(); cur.close()
    out=[]
    for r in rows:
        out.append({"id": r["id"], "title": r["title"]} if isinstance(r,sqlite3.Row) else {"id": r[0],"title": r[1]})
    return out

def get_recipe(recipe_id: int) -> Optional[Dict[str,Any]]:
    con=_conn(); cur=con.cursor()
    if _engine()=="postgres":
        cur.execute("""SELECT id,title,ingredients,instructions,image_bytes,image_mime,
                       image_filename,serves,created_at,updated_at FROM recipes WHERE id=%s;""",(recipe_id,))
    else:
        cur.execute("""SELECT id,title,ingredients,instructions,image_bytes,image_mime,
                       image_filename,serves,created_at,updated_at FROM recipes WHERE id=?;""",(recipe_id,))
    row=cur.fetchone(); cur.close()
    if not row: return None
    if isinstance(row, sqlite3.Row): d=dict(row)
    else:
        d={"id":row[0],"title":row[1],"ingredients":row[2],"instructions":row[3],
           "image_bytes":row[4],"image_mime":row[5],"image_filename":row[6],
           "serves":row[7],"created_at":row[8],"updated_at":row[9]}
    d.setdefault("servings", d.get("serves",0))
    return d

def update_recipe(*, recipe_id:int, title:Optional[str]=None, ingredients:Optional[str]=None,
                  instructions:Optional[str]=None, image_bytes:Optional[bytes]=None,
                  image_mime:Optional[str]=None, image_filename:Optional[str]=None,
                  keep_existing_image:bool=True, serves:Optional[int]=None, servings:Optional[int]=None) -> None:
    con=_conn(_
