Skip to content
Chat history
# pages/cookbook.py
import streamlit as st
from food.db import init_db, add_recipe, list_recipes, get_recipe, update_recipe

# Ensure DB exists / migrated on each load
init_db()

# --- session state for edit mode ---
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

def render():
    st.title("🍳 Cook Book")

    # ========== CREATE ==========
    with st.form("new_recipe_form", clear_on_submit=True):
        st.subheader("Add a new recipe")

        title = st.text_input("Title *", placeholder="e.g., Lemon Garlic Chicken")
        description = st.text_area("Short Description", placeholder="Optional notes...")
        ingredients = st.text_area(
            "Ingredients (one per line, optional)",
            placeholder="Optional: 2 chicken breasts\n1 lemon (zest & juice)\n..."
        )
        steps = st.text_area(
            "Steps (one per line, optional)",
            placeholder="Optional: Preheat oven to 200°C\nMix marinade\n..."
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=0, key="new_prep")
        with col2:
            cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=0, key="new_cook")
        with col3:
            servings = st.number_input("Servings", min_value=1, step=1, value=1, key="new_servings")

        tags = st.text_input("Tags (comma separated, optional)", placeholder="e.g., chicken, quick", key="new_tags")

        submitted = st.form_submit_button("Save Recipe")

        if submitted:
            if not title.strip():
                st.error("Please provide a title.")
            else:
                try:
                    new_id = add_recipe(
                        title=title.strip(),
                        description=(description or "").strip(),
                        ingredients=(ingredients or "").strip(),
                        steps=(steps or "").strip(),
                        tags=(tags or "").strip(),
                        prep_minutes=int(prep_minutes or 0),
                        cook_minutes=int(cook_minutes or 0),
                        servings=int(servings or 1),
                    )
                    st.success(f"Recipe saved ✅ (ID: {new_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save recipe: {e}")

    st.divider()

    # ========== EDIT PANEL ==========
    if st.session_state.edit_id is not None:
        rid = st.session_state.edit_id
        rec = get_recipe(rid)
        if not rec:
            st.warning("Recipe not found.")
            st.session_state.edit_id = None
        else:
            st.subheader(f"✏️ Edit recipe: {rec['title']} (ID {rid})")

            with st.form("edit_recipe_form"):
                etitle = st.text_input("Title *", value=rec["title"])
                edescription = st.text_area("Short Description", value=rec.get("description") or "")
                eingredients = st.text_area("Ingredients (one per line, optional)", value=rec.get("ingredients") or "")
                esteps = st.text_area("Steps (one per line, optional)", value=rec.get("steps") or "")

                col1, col2, col3 = st.columns(3)
                with col1:
                    e_prep = st.number_input("Prep (min)", min_value=0, step=5, value=int(rec.get("prep_minutes") or 0))
                with col2:
                    e_cook = st.number_input("Cook (min)", min_value=0, step=5, value=int(rec.get("cook_minutes") or 0))
                with col3:
                    e_serv = st.number_input("Servings", min_value=1, step=1, value=int(rec.get("servings") or 1))

                e_tags = st.text_input("Tags (comma separated, optional)", value=rec.get("tags") or "")

                c1, c2 = st.columns(2)
                save_edit = c1.form_submit_button("Save changes ✅")
                cancel_edit = c2.form_submit_button("Cancel")

                if save_edit:
                    if not etitle.strip():
                        st.error("Please provide a title.")
                    else:
                        try:
                            changed = update_recipe(
                                recipe_id=rid,
                                title=etitle.strip(),
                                description=(edescription or "").strip(),
                                ingredients=(eingredients or "").strip(),
                                steps=(esteps or "").strip(),
                                tags=(e_tags or "").strip(),
                                prep_minutes=int(e_prep or 0),
                                cook_minutes=int(e_cook or 0),
                                servings=int(e_serv or 1),
                            )
                            if changed:
                                st.success("Recipe updated ✅")
                            else:
                                st.info("No changes detected.")
                            st.session_state.edit_id = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not update recipe: {e}")

                if cancel_edit:
                    st.session_state.edit_id = None
                    st.rerun()

    # ========== LIST / SEARCH ==========
    st.subheader("Your recipes")
    search = st.text_input("Search (title or tags)", key="recipe_search")
    rows = list_recipes(limit=200, search=(search.strip() or None))

    if not rows:
        st.info("No recipes found yet. Add your first one above.")
    else:
        for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows:
            total_time = (rprep or 0) + (rcook or 0)
            header = f"{rtitle}  •  {rserv} servings  •  {total_time} min total"
            with st.expander(header):
                st.caption(f"Tags: {rtags or '—'}  |  Added: {rcreated}")

                r = get_recipe(rid)
                if not r:
                    st.warning("Could not load this recipe’s details.")
                    continue

                if (r.get("description") or "").strip():
                    st.markdown("**Notes**")
                    st.write(r["description"])

                if (r.get("ingredients") or "").strip():
                    st.markdown("**Ingredients**")
                    st.markdown("\n".join(
                        f"- {line}" for line in r["ingredients"].splitlines() if line.strip()
                    ))

                if (r.get("steps") or "").strip():
                    st.markdown("**Steps**")
                    st.markdown("\n".join(
                        f"{i+1}. {line}"
                        for i, line in enumerate([ln for ln in r["steps"].splitlines() if ln.strip()])
                    ))

                # Edit button for this recipe
                if st.button("✏️ Edit this recipe", key=f"edit_btn_{rid}"):
                    st.session_state.edit_id = rid
                    st.rerun()

You said:
I'm having issue while testing app in streamlit.app. There is this error message and its in file streamlit.app ImportError: cannot import name 'create_db_and_tables' from 'food.db' 

(/mount/src/food_planner/food/db.py)

2025-08-19 19:43:39.839 503 GET /script-health-check (127.0.0.1) 188.63ms
ChatGPT said:
Ah, I see exactly what’s happening. That error:

ImportError: cannot import name 'create_db_and_tables' from 'food.db'
tells us that Streamlit is trying to import a function create_db_and_tables from your food/db.py file, but it can’t find it. The problem is almost always one of these three:

1️⃣ The function doesn’t exist in db.py
Check your food/db.py. You need to have something like:

from sqlmodel import SQLModel, create_engine

# Example function
def create_db_and_tables():
    engine = create_engine("sqlite:///food.db")
    SQLModel.metadata.create_all(engine)
If create_db_and_tables isn’t defined in db.py, the import will fail.

2️⃣ Wrong path / module confusion
Streamlit is running inside its container, and the path matters. In your import:

from food.db import create_db_and_tables
food must be a folder with __init__.py inside (even if empty) so Python treats it as a package.

db.py must be in that folder.

If db.py is not at food/db.py (e.g., you moved it), you need to update the import everywhere.

Check structure:

food_planner/
 ├─ streamlit_app.py
 └─ food/
     ├─ __init__.py
     └─ db.py
3️⃣ Circular import issue
If db.py imports something from streamlit_app.py (directly or indirectly), Python can’t load the function yet. Make sure db.py is independent.

✅ How to fix
Verify that db.py contains the function:

def create_db_and_tables():
    from sqlmodel import SQLModel, create_engine
    engine = create_engine("sqlite:///food.db")
    SQLModel.metadata.create_all(engine)
Make sure __init__.py exists in the food folder.

Check the import in your Streamlit app:

from food.db import create_db_and_tables
Restart the Streamlit server (important – it caches imports sometimes):

streamlit run streamlit_app.py
If you want, I can rewrite a correct db.py for your current app structure so the create_db_and_tables import works reliably in Streamlit, even in their deployment container.

Do you want me to do that?

You said:
 here is my db.py file: # food/db.py

from pathlib import Path
import sqlite3
from typing import List, Tuple, Optional, Dict, Any

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "food_planner.db"

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def _table_info(conn: sqlite3.Connection, table: str):
    return conn.execute(f"PRAGMA table_info({table});").fetchall()

def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                ingredients TEXT,
                steps TEXT,
                tags TEXT,
                prep_minutes INTEGER DEFAULT 0,
                cook_minutes INTEGER DEFAULT 0,
                servings INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

        # (Optional) old-schema migration kept from earlier messages — safe to omit if fresh DB
        info = _table_info(conn, "recipes")
        if info:
            col = {row[1]: row for row in info}
            needs_migration = any(col.get(n, (None, None, None, 0))[3] == 1 for n in ("ingredients", "steps"))
            if needs_migration:
                conn.execute("BEGIN;")
                conn.execute(
                    """
                    CREATE TABLE recipes_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        ingredients TEXT,
                        steps TEXT,
                        tags TEXT,
                        prep_minutes INTEGER DEFAULT 0,
                        cook_minutes INTEGER DEFAULT 0,
                        servings INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT INTO recipes_new
                        (id, title, description, ingredients, steps, tags,
                         prep_minutes, cook_minutes, servings, created_at)
                    SELECT id, title, description, ingredients, steps, tags,
                           prep_minutes, cook_minutes, servings, created_at
                    FROM recipes;
                    """
                )
                conn.execute("DROP TABLE recipes;")
                conn.execute("ALTER TABLE recipes_new RENAME TO recipes;")
                conn.commit()

def add_recipe(
    title: str,
    description: str = "",
    ingredients: str = "",
    steps: str = "",
    tags: str = "",
    prep_minutes: int = 0,
    cook_minutes: int = 0,
    servings: int = 1,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO recipes
                (title, description, ingredients, steps, tags,
                 prep_minutes, cook_minutes, servings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (title or "").strip(),
                (description or "").strip(),
                (ingredients or "").strip(),
                (steps or "").strip(),
                (tags or "").strip(),
                int(prep_minutes or 0),
                int(cook_minutes or 0),
                int(servings or 1),
            ),
        )
        conn.commit()
        return cur.lastrowid

def update_recipe(
    recipe_id: int,
    title: str,
    description: str = "",
    ingredients: str = "",
    steps: str = "",
    tags: str = "",
    prep_minutes: int = 0,
    cook_minutes: int = 0,
    servings: int = 1,
) -> int:
    """Update a recipe. Returns number of rows affected (0 or 1)."""
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE recipes
            SET title = ?, description = ?, ingredients = ?, steps = ?, tags = ?,
                prep_minutes = ?, cook_minutes = ?, servings = ?
            WHERE id = ?
            """,
            (
                (title or "").strip(),
                (description or "").strip(),
                (ingredients or "").strip(),
                (steps or "").strip(),
                (tags or "").strip(),
                int(prep_minutes or 0),
                int(cook_minutes or 0),
                int(servings or 1),
                int(recipe_id),
            ),
        )
        conn.commit()
        return cur.rowcount

def list_recipes(limit: int = 100, search: Optional[str] = None) -> List[Tuple]:
    with _connect() as conn:
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """
                SELECT id, title, tags, servings, prep_minutes, cook_minutes, created_at
                FROM recipes
                WHERE title LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, title, tags, servings, prep_minutes, cook_minutes, created_at
                FROM recipes
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return rows

def get_recipe(recipe_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, title, description, ingredients, steps, tags,
                   prep_minutes, cook_minutes, servings, created_at
            FROM recipes WHERE id = ?
            """,
            (recipe_id,),
        ).fetchone()
    if not row:
        return None
    keys = [
        "id","title","description","ingredients","steps","tags",
        "prep_minutes","cook_minutes","servings","created_at"
    ]
    return dict(zip(keys, row))
ChatGPT said:
Perfect — now I see exactly why Streamlit fails.

Your current db.py does not have a function called create_db_and_tables. You have init_db() instead.

When your app does:

from food.db import create_db_and_tables
Python says: “I don’t know any create_db_and_tables here”. That’s exactly your ImportError.

🔹 Two ways to fix
Option 1: Rename init_db to create_db_and_tables
In food/db.py, just rename:

def create_db_and_tables() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                ingredients TEXT,
                steps TEXT,
                tags TEXT,
                prep_minutes INTEGER DEFAULT 0,
                cook_minutes INTEGER DEFAULT 0,
                servings INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
        # migration logic remains unchanged
        info = _table_info(conn, "recipes")
        if info:
            col = {row[1]: row for row in info}
            needs_migration = any(col.get(n, (None, None, None, 0))[3] == 1 for n in ("ingredients", "steps"))
            if needs_migration:
                conn.execute("BEGIN;")
                conn.execute(
                    """
                    CREATE TABLE recipes_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        ingredients TEXT,
                        steps TEXT,
                        tags TEXT,
                        prep_minutes INTEGER DEFAULT 0,
                        cook_minutes INTEGER DEFAULT 0,
                        servings INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT INTO recipes_new
                        (id, title, description, ingredients, steps, tags,
                         prep_minutes, cook_minutes, servings, created_at)
                    SELECT id, title, description, ingredients, steps, tags,
                           prep_minutes, cook_minutes, servings, created_at
                    FROM recipes;
                    """
                )
                conn.execute("DROP TABLE recipes;")
                conn.execute("ALTER TABLE recipes_new RENAME TO recipes;")
                conn.commit()
Then your import in the Streamlit app works exactly as it expects:

from food.db import create_db_and_tables
Option 2: Keep init_db() and change your Streamlit import
If you prefer keeping the name init_db(), then in your streamlit_app.py or wherever you import, change:

from food.db import init_db as create_db_and_tables
This way you don’t touch your existing db.py, but the app still sees create_db_and_tables.

💡 Tip: After changing, always restart Streamlit:

streamlit run streamlit_app.py
Otherwise it may still cache the old import.

If you want, I can rewrite a clean version of db.py that includes create_db_and_tables and keeps all your current functionality (add/update/list/get recipes) fully compatible with Streamlit deployment. It will remove any future import headaches.

Do you want me to do that?

You said:
I have issue in streamlit app AttributeError: module 'pages.cookbook' has no attribute 'render' 

2025-08-19 19:50:54.922 503 GET /script-hea
ChatGPT said:
Ah! This is a classic Streamlit “pages” import issue. The error:

AttributeError: module 'pages.cookbook' has no attribute 'render'
means Streamlit is trying to call pages.cookbook.render(), but your pages/cookbook.py file does not define a function named render().

Why this happens
In multi-page Streamlit apps, there are two ways to structure your pages:

Using the built-in “Pages” system (files inside pages/ folder):

Each .py file is automatically a page in the app.

Streamlit expects the code at top-level, it does not require a render() function.

Example:

# pages/cookbook.py
import streamlit as st

st.title("Cookbook Page")
st.write("Here is my cookbook!")
Streamlit runs the file directly; no need for render().

Using a manual page system (your own streamlit_app.py imports pages and calls them):

Then each page must have a render() function.

Example:

# pages/cookbook.py
import streamlit as st

def render():
    st.title("Cookbook Page")
    st.write("Here is my cookbook!")
Then in streamlit_app.py:

from pages import cookbook

cookbook.render()  # This works only if render() exists
🔹 How to fix your error
Option 1: You want top-level Streamlit pages

Remove any render() calls in your streamlit_app.py.

Just let Streamlit run pages/cookbook.py as its own page.

Option 2: You want manual page switching with render()

Add render() in pages/cookbook.py:

import streamlit as st
from food.cookbook import show_cookbook  # example function that handles cookbook logic

def render():
    st.title("Cookbook")
    show_cookbook()
Ensure every page you import manually has the same render() function.

💡 Tip:

Streamlit auto-detects pages if you have a folder pages/ with .py files.

Only use render() if you want to control page rendering manually.

I can rewrite your pages/cookbook.py properly for Streamlit deployment so it works either way, keeping your cookbook functions (add, list, edit) fully compatible.

Do you want me to do that?

You said:
Please adjust my stramlit_app.py # streamlit_app.py
import streamlit as st
from food.db import init_db
from pages import cookbook, food_plan, shopping_list

st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="wide")
st.title("🍽️ Food Planner")

# Create tables if first run
# create_db_and_tables()

tab1, tab2, tab3 = st.tabs(["Cook Book", "Food Plan", "Shopping List"])
with tab1: cookbook.render()
with tab2: food_plan.render()
with tab3: shopping_list.render()
ChatGPT said:
Perfect, now I understand exactly what your app is trying to do. Right now, the problem is that your pages/*.py files don’t have a render() function, but your streamlit_app.py calls cookbook.render(), food_plan.render(), etc.

We can adjust your streamlit_app.py to:

Use your existing init_db() from food.db.

Ensure pages/*.py have a render() function for each page.

Keep the st.tabs layout.

Here’s a corrected version of streamlit_app.py:

# streamlit_app.py
import streamlit as st
from food.db import init_db

# Import page modules (make sure each has a render() function)
from pages import cookbook, food_plan, shopping_list

# Set page config
st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="wide")
st.title("🍽️ Food Planner")

# Initialize database (creates tables on first run)
init_db()  # this replaces create_db_and_tables

# Create tabs for pages
tab1, tab2, tab3 = st.tabs(["Cook Book", "Food Plan", "Shopping List"])

with tab1:
    cookbook.render()        # cookbook.py must have a render() function

with tab2:
    food_plan.render()       # food_plan.py must have a render() function

with tab3:
    shopping_list.render()   # shopping_list.py must have a render() function
✅ What you need in each page (pages/*.py)
Example pages/cookbook.py:

import streamlit as st
from food.db import list_recipes, get_recipe

def render():
    st.header("Cook Book")
    
    recipes = list_recipes(limit=50)
    for r in recipes:
        st.write(f"**{r[1]}** - Tags: {r[2]}, Servings: {r[3]}")
Do the same for food_plan.py and shopping_list.py: just define a render() function that contains the Streamlit code for that page.

If you want, I can write all three pages/*.py with render() functions fully ready, so your tabs work perfectly with your current DB structure.

Do you want me to do that?

You said:
can you adjust my cookbook.py so it works properly? # pages/cookbook.py  (or pages/1_Cook_Book.py)

import streamlit as st
from food.db import (
    init_db,
    add_recipe,
    list_recipes,
    get_recipe,
    update_recipe,
)

# Ensure DB exists / migrated on each load
init_db()

st.title("🍳 Cook Book")

# --- session state for edit mode ---
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# ========== CREATE ==========
with st.form("new_recipe_form", clear_on_submit=True):
    st.subheader("Add a new recipe")

    title = st.text_input("Title *", placeholder="e.g., Lemon Garlic Chicken")
    description = st.text_area("Short Description", placeholder="Optional notes...")
    ingredients = st.text_area(
        "Ingredients (one per line, optional)",
        placeholder="Optional: 2 chicken breasts\n1 lemon (zest & juice)\n..."
    )
    steps = st.text_area(
        "Steps (one per line, optional)",
        placeholder="Optional: Preheat oven to 200°C\nMix marinade\n..."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=0, key="new_prep")
    with col2:
        cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=0, key="new_cook")
    with col3:
        servings = st.number_input("Servings", min_value=1, step=1, value=1, key="new_servings")

    tags = st.text_input("Tags (comma separated, optional)", placeholder="e.g., chicken, quick", key="new_tags")

    submitted = st.form_submit_button("Save Recipe")

    if submitted:
        if not title.strip():
            st.error("Please provide a title.")
        else:
            try:
                new_id = add_recipe(
                    title=title.strip(),
                    description=(description or "").strip(),
                    ingredients=(ingredients or "").strip(),   # optional
                    steps=(steps or "").strip(),               # optional
                    tags=(tags or "").strip(),
                    prep_minutes=int(prep_minutes or 0),
                    cook_minutes=int(cook_minutes or 0),
                    servings=int(servings or 1),
                )
                st.success(f"Recipe saved ✅ (ID: {new_id})")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save recipe: {e}")

st.divider()

# ========== EDIT PANEL ==========
if st.session_state.edit_id is not None:
    rid = st.session_state.edit_id
    rec = get_recipe(rid)
    if not rec:
        st.warning("Recipe not found.")
        st.session_state.edit_id = None
    else:
        st.subheader(f"✏️ Edit recipe: {rec['title']} (ID {rid})")

        with st.form("edit_recipe_form"):
            etitle = st.text_input("Title *", value=rec["title"])
            edescription = st.text_area("Short Description", value=rec.get("description") or "")
            eingredients = st.text_area("Ingredients (one per line, optional)", value=rec.get("ingredients") or "")
            esteps = st.text_area("Steps (one per line, optional)", value=rec.get("steps") or "")

            col1, col2, col3 = st.columns(3)
            with col1:
                e_prep = st.number_input("Prep (min)", min_value=0, step=5, value=int(rec.get("prep_minutes") or 0))
            with col2:
                e_cook = st.number_input("Cook (min)", min_value=0, step=5, value=int(rec.get("cook_minutes") or 0))
            with col3:
                e_serv = st.number_input("Servings", min_value=1, step=1, value=int(rec.get("servings") or 1))

            e_tags = st.text_input("Tags (comma separated, optional)", value=rec.get("tags") or "")

            c1, c2 = st.columns(2)
            save_edit = c1.form_submit_button("Save changes ✅")
            cancel_edit = c2.form_submit_button("Cancel")

            if save_edit:
                if not etitle.strip():
                    st.error("Please provide a title.")
                else:
                    try:
                        changed = update_recipe(
                            recipe_id=rid,
                            title=etitle.strip(),
                            description=(edescription or "").strip(),
                            ingredients=(eingredients or "").strip(),
                            steps=(esteps or "").strip(),
                            tags=(e_tags or "").strip(),
                            prep_minutes=int(e_prep or 0),
                            cook_minutes=int(e_cook or 0),
                            servings=int(e_serv or 1),
                        )
                        if changed:
                            st.success("Recipe updated ✅")
                        else:
                            st.info("No changes detected.")
                        st.session_state.edit_id = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update recipe: {e}")

            if cancel_edit:
                st.session_state.edit_id = None
                st.rerun()

# ========== LIST / SEARCH ==========
st.subheader("Your recipes")
search = st.text_input("Search (title or tags)", key="recipe_search")
rows = list_recipes(limit=200, search=(search.strip() or None))

if not rows:
    st.info("No recipes found yet. Add your first one above.")
else:
    for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows:
        total_time = (rprep or 0) + (rcook or 0)
        header = f"{rtitle}  •  {rserv} servings  •  {total_time} min total"
        with st.expander(header):
            st.caption(f"Tags: {rtags or '—'}  |  Added: {rcreated}")

            r = get_recipe(rid)
            if not r:
                st.warning("Could not load this recipe’s details.")
                continue

            if (r.get("description") or "").strip():
                st.markdown("**Notes**")
                st.write(r["description"])

            if (r.get("ingredients") or "").strip():
                st.markdown("**Ingredients**")
                st.markdown("\n".join(
                    f"- {line}" for line in r["ingredients"].splitlines() if line.strip()
                ))

            if (r.get("steps") or "").strip():
                st.markdown("**Steps**")
                st.markdown("\n".join(
                    f"{i+1}. {line}"
                    for i, line in enumerate([ln for ln in r["steps"].splitlines() if ln.strip()])
                ))

            # Edit button for this recipe
            if st.button("✏️ Edit this recipe", key=f"edit_btn_{rid}"):
                st.session_state.edit_id = rid
                st.rerun()
ChatGPT said:
Perfect! The main reason your streamlit_app.py failed with

AttributeError: module 'pages.cookbook' has no attribute 'render'
is that your pages/cookbook.py currently doesn’t define a render() function. Streamlit was expecting something like:

cookbook.render()
but there is no render() in your file yet.

We can fix this by wrapping your entire current code inside a render() function and removing any top-level Streamlit calls outside of it. Then streamlit_app.py can just call cookbook.render().

Here’s the adjusted pages/cookbook.py:

# pages/cookbook.py
import streamlit as st
from food.db import init_db, add_recipe, list_recipes, get_recipe, update_recipe

# Ensure DB exists / migrated on each load
init_db()

# --- session state for edit mode ---
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

def render():
    st.title("🍳 Cook Book")

    # ========== CREATE ==========
    with st.form("new_recipe_form", clear_on_submit=True):
        st.subheader("Add a new recipe")

        title = st.text_input("Title *", placeholder="e.g., Lemon Garlic Chicken")
        description = st.text_area("Short Description", placeholder="Optional notes...")
        ingredients = st.text_area(
            "Ingredients (one per line, optional)",
            placeholder="Optional: 2 chicken breasts\n1 lemon (zest & juice)\n..."
        )
        steps = st.text_area(
            "Steps (one per line, optional)",
            placeholder="Optional: Preheat oven to 200°C\nMix marinade\n..."
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=0, key="new_prep")
        with col2:
            cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=0, key="new_cook")
        with col3:
            servings = st.number_input("Servings", min_value=1, step=1, value=1, key="new_servings")

        tags = st.text_input("Tags (comma separated, optional)", placeholder="e.g., chicken, quick", key="new_tags")

        submitted = st.form_submit_button("Save Recipe")

        if submitted:
            if not title.strip():
                st.error("Please provide a title.")
            else:
                try:
                    new_id = add_recipe(
                        title=title.strip(),
                        description=(description or "").strip(),
                        ingredients=(ingredients or "").strip(),
                        steps=(steps or "").strip(),
                        tags=(tags or "").strip(),
                        prep_minutes=int(prep_minutes or 0),
                        cook_minutes=int(cook_minutes or 0),
                        servings=int(servings or 1),
                    )
                    st.success(f"Recipe saved ✅ (ID: {new_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save recipe: {e}")

    st.divider()

    # ========== EDIT PANEL ==========
    if st.session_state.edit_id is not None:
        rid = st.session_state.edit_id
        rec = get_recipe(rid)
        if not rec:
            st.warning("Recipe not found.")
            st.session_state.edit_id = None
        else:
            st.subheader(f"✏️ Edit recipe: {rec['title']} (ID {rid})")

            with st.form("edit_recipe_form"):
                etitle = st.text_input("Title *", value=rec["title"])
                edescription = st.text_area("Short Description", value=rec.get("description") or "")
                eingredients = st.text_area("Ingredients (one per line, optional)", value=rec.get("ingredients") or "")
                esteps = st.text_area("Steps (one per line, optional)", value=rec.get("steps") or "")

                col1, col2, col3 = st.columns(3)
                with col1:
                    e_prep = st.number_input("Prep (min)", min_value=0, step=5, value=int(rec.get("prep_minutes") or 0))
                with col2:
                    e_cook = st.number_input("Cook (min)", min_value=0, step=5, value=int(rec.get("cook_minutes") or 0))
                with col3:
                    e_serv = st.number_input("Servings", min_value=1, step=1, value=int(rec.get("servings") or 1))

                e_tags = st.text_input("Tags (comma separated, optional)", value=rec.get("tags") or "")

                c1, c2 = st.columns(2)
                save_edit = c1.form_submit_button("Save changes ✅")
                cancel_edit = c2.form_submit_button("Cancel")

                if save_edit:
                    if not etitle.strip():
                        st.error("Please provide a title.")
                    else:
                        try:
                            changed = update_recipe(
                                recipe_id=rid,
                                title=etitle.strip(),
                                description=(edescription or "").strip(),
                                ingredients=(eingredients or "").strip(),
                                steps=(esteps or "").strip(),
                                tags=(e_tags or "").strip(),
                                prep_minutes=int(e_prep or 0),
                                cook_minutes=int(e_cook or 0),
                                servings=int(e_serv or 1),
                            )
                            if changed:
                                st.success("Recipe updated ✅")
                            else:
                                st.info("No changes detected.")
                            st.session_state.edit_id = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not update recipe: {e}")

                if cancel_edit:
                    st.session_state.edit_id = None
                    st.rerun()

    # ========== LIST / SEARCH ==========
    st.subheader("Your recipes")
    search = st.text_input("Search (title or tags)", key="recipe_search")
    rows = list_recipes(limit=200, search=(search.strip() or None))

    if not rows:
        st.info("No recipes found yet. Add your first one above.")
    else:
        for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows:
            total_time = (rprep or 0) + (rcook or 0)
            header = f"{rtitle}  •  {rserv} servings  •  {total_time} min total"
            with st.expander(header):
                st.caption(f"Tags: {rtags or '—'}  |  Added: {rcreated}")

                r = get_recipe(rid)
                if not r:
                    st.warning("Could not load this recipe’s details.")
                    continue

                if (r.get("description") or "").strip():
                    st.markdown("**Notes**")
                    st.write(r["description"])

                if (r.get("ingredients") or "").strip():
                    st.markdown("**Ingredients**")
                    st.markdown("\n".join(
                        f"- {line}" for line in r["ingredients"].splitlines() if line.strip()
                    ))

                if (r.get("steps") or "").strip():
                    st.markdown("**Steps**")
                    st.markdown("\n".join(
                        f"{i+1}. {line}"
                        for i, line in enumerate([ln for ln in r["steps"].splitlines() if ln.strip()])
                    ))

                # Edit button for this recipe
                if st.button("✏️ Edit this recipe", key=f"edit_btn_{rid}"):
                    st.session_state.edit_id = rid
                    st.rerun()
✅ Key changes:
Wrapped all top-level Streamlit code inside a render() function.

Left init_db() at the top so DB is created on app start.

Your streamlit_app.py can now safely do:

import cookbook
cookbook.render()
If you want, I can also rewrite food_plan.py and shopping_list.py with empty render() stubs so your tabs work immediately without errors. This way your app will run without crashing.

Do you want me to do that next?




No file chosenNo file chosen
ChatGPT can make mistakes. Check important info. See Cookie Preferences.
ChatGPT says: Perfect! The main reason your `streamlit_app.py` failed with ``` AttributeError: module 'pages.cookbook' has no attribute 'render' ``` is that your `pages/cookbook.py` currently **doesn’t define a `render()` function**. Streamlit was expecting something like: ```python cookbook.render() ``` but there is no `render()` in your file yet. We can fix this by **wrapping your entire current code inside a `render()` function** and removing any top-level Streamlit calls outside of it. Then `streamlit_app.py` can just call `cookbook.render()`. Here’s the **adjusted `pages/cookbook.py`**: ```python # pages/cookbook.py import streamlit as st from food.db import init_db, add_recipe, list_recipes, get_recipe, update_recipe # Ensure DB exists / migrated on each load init_db() # --- session state for edit mode --- if "edit_id" not in st.session_state: st.session_state.edit_id = None def render(): st.title("🍳 Cook Book") # ========== CREATE ========== with st.form("new_recipe_form", clear_on_submit=True): st.subheader("Add a new recipe") title = st.text_input("Title *", placeholder="e.g., Lemon Garlic Chicken") description = st.text_area("Short Description", placeholder="Optional notes...") ingredients = st.text_area( "Ingredients (one per line, optional)", placeholder="Optional: 2 chicken breasts\n1 lemon (zest & juice)\n..." ) steps = st.text_area( "Steps (one per line, optional)", placeholder="Optional: Preheat oven to 200°C\nMix marinade\n..." ) col1, col2, col3 = st.columns(3) with col1: prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=0, key="new_prep") with col2: cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=0, key="new_cook") with col3: servings = st.number_input("Servings", min_value=1, step=1, value=1, key="new_servings") tags = st.text_input("Tags (comma separated, optional)", placeholder="e.g., chicken, quick", key="new_tags") submitted = st.form_submit_button("Save Recipe") if submitted: if not title.strip(): st.error("Please provide a title.") else: try: new_id = add_recipe( title=title.strip(), description=(description or "").strip(), ingredients=(ingredients or "").strip(), steps=(steps or "").strip(), tags=(tags or "").strip(), prep_minutes=int(prep_minutes or 0), cook_minutes=int(cook_minutes or 0), servings=int(servings or 1), ) st.success(f"Recipe saved ✅ (ID: {new_id})") st.rerun() except Exception as e: st.error(f"Could not save recipe: {e}") st.divider() # ========== EDIT PANEL ========== if st.session_state.edit_id is not None: rid = st.session_state.edit_id rec = get_recipe(rid) if not rec: st.warning("Recipe not found.") st.session_state.edit_id = None else: st.subheader(f"✏️ Edit recipe: {rec['title']} (ID {rid})") with st.form("edit_recipe_form"): etitle = st.text_input("Title *", value=rec["title"]) edescription = st.text_area("Short Description", value=rec.get("description") or "") eingredients = st.text_area("Ingredients (one per line, optional)", value=rec.get("ingredients") or "") esteps = st.text_area("Steps (one per line, optional)", value=rec.get("steps") or "") col1, col2, col3 = st.columns(3) with col1: e_prep = st.number_input("Prep (min)", min_value=0, step=5, value=int(rec.get("prep_minutes") or 0)) with col2: e_cook = st.number_input("Cook (min)", min_value=0, step=5, value=int(rec.get("cook_minutes") or 0)) with col3: e_serv = st.number_input("Servings", min_value=1, step=1, value=int(rec.get("servings") or 1)) e_tags = st.text_input("Tags (comma separated, optional)", value=rec.get("tags") or "") c1, c2 = st.columns(2) save_edit = c1.form_submit_button("Save changes ✅") cancel_edit = c2.form_submit_button("Cancel") if save_edit: if not etitle.strip(): st.error("Please provide a title.") else: try: changed = update_recipe( recipe_id=rid, title=etitle.strip(), description=(edescription or "").strip(), ingredients=(eingredients or "").strip(), steps=(esteps or "").strip(), tags=(e_tags or "").strip(), prep_minutes=int(e_prep or 0), cook_minutes=int(e_cook or 0), servings=int(e_serv or 1), ) if changed: st.success("Recipe updated ✅") else: st.info("No changes detected.") st.session_state.edit_id = None st.rerun() except Exception as e: st.error(f"Could not update recipe: {e}") if cancel_edit: st.session_state.edit_id = None st.rerun() # ========== LIST / SEARCH ========== st.subheader("Your recipes") search = st.text_input("Search (title or tags)", key="recipe_search") rows = list_recipes(limit=200, search=(search.strip() or None)) if not rows: st.info("No recipes found yet. Add your first one above.") else: for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows: total_time = (rprep or 0) + (rcook or 0) header = f"{rtitle} • {rserv} servings • {total_time} min total" with st.expander(header): st.caption(f"Tags: {rtags or '—'} | Added: {rcreated}") r = get_recipe(rid) if not r: st.warning("Could not load this recipe’s details.") continue if (r.get("description") or "").strip(): st.markdown("**Notes**") st.write(r["description"]) if (r.get("ingredients") or "").strip(): st.markdown("**Ingredients**") st.markdown("\n".join( f"- {line}" for line in r["ingredients"].splitlines() if line.strip() )) if (r.get("steps") or "").strip(): st.markdown("**Steps**") st.markdown("\n".join( f"{i+1}. {line}" for i, line in enumerate([ln for ln in r["steps"].splitlines() if ln.strip()]) )) # Edit button for this recipe if st.button("✏️ Edit this recipe", key=f"edit_btn_{rid}"): st.session_state.edit_id = rid st.rerun() ``` --- ### ✅ Key changes: 1. Wrapped **all top-level Streamlit code** inside a `render()` function. 2. Left `init_db()` at the top so DB is created on app start. 3. Your `streamlit_app.py` can now safely do: ```python import cookbook cookbook.render() ``` --- If you want, I can **also rewrite `food_plan.py` and `shopping_list.py` with empty render() stubs** so your tabs work immediately without errors. This way your app will run without crashing. Do you want me to do that next?
