# pages/cookbook.py
import streamlit as st
import string
from typing import List, Dict, Any, Optional

# --- DB imports (expects these to exist in food/db.py) ---
from food.db import (
    init_db,
    add_recipe,
    list_recipes,
    get_recipe,
    update_recipe,
)

# Try to import delete if available
try:
    from food.db import delete_recipe  # type: ignore
except Exception:  # noqa: BLE001
    delete_recipe = None  # we'll handle gracefully

# Ensure DB is ready
init_db()

# ---------- Utilities ----------
def _normalize_title(r: Any) -> str:
    """Best-effort way to get a recipe title regardless of shape."""
    if isinstance(r, dict):
        return str(r.get("title") or r.get("name") or r.get("Title") or "")
    if isinstance(r, (list, tuple)):
        # guess: (id, title, ...)
        return str(r[1]) if len(r) > 1 else str(r[0])
    return str(r)

def _get_id(r: Any) -> Any:
    """Best-effort way to get the recipe id."""
    if isinstance(r, dict):
        return r.get("id") or r.get("recipe_id") or r.get("ID")
    if isinstance(r, (list, tuple)):
        # guess: (id, title, ...)
        return r[0]
    return None

def _group_by_letter(recipes: List[Any]) -> Dict[str, List[Any]]:
    buckets: Dict[str, List[Any]] = {ch: [] for ch in string.ascii_uppercase}
    for r in recipes:
        t = _normalize_title(r).strip()
        if not t:
            continue
        first = t[0].upper()
        key = first if first in buckets else "Z"  # dump non A-Z under Z
        buckets[key].append(r)
    # sort each bucket by title
    for k in buckets:
        buckets[k].sort(key=lambda x: _normalize_title(x).lower())
    return buckets

def _filter_by_query(recipes: List[Any], q: str) -> List[Any]:
    q = q.strip().lower()
    if not q:
        return recipes
    return [r for r in recipes if q in _normalize_title(r).lower()]

# ---------- Session State ----------
if "cb_selected_id" not in st.session_state:
    st.session_state.cb_selected_id = None  # currently opened recipe id
if "cb_mode" not in st.session_state:
    st.session_state.cb_mode = "list"  # "list" | "view" | "edit" | "add"
if "cb_confirm_delete_id" not in st.session_state:
    st.session_state.cb_confirm_delete_id = None
if "cb_query" not in st.session_state:
    st.session_state.cb_query = ""

# ---------- UI ----------
st.header("Cook Book", divider="gray")

# Load all recipes once per render
all_recipes: List[Any] = list_recipes() or []
total = len(all_recipes)

st.caption(f"You have **{total}** recipe{'s' if total != 1 else ''} in your cook book.")

# Search + actions row
left, right = st.columns([3, 2])
with left:
    st.session_state.cb_query = st.text_input(
        "Search recipes", 
        value=st.session_state.cb_query, 
        placeholder="Start typing… e.g., 'chi' for 'Chicken'",
    )

with right:
    btn_cols = st.columns([1, 1, 1, 1])
    with btn_cols[0]:
        if st.button("➕ Add recipe", use_container_width=True):
            st.session_state.cb_mode = "add"
            st.session_state.cb_selected_id = None
            st.session_state.cb_confirm_delete_id = None

    # You can easily add more buttons later:
    # with btn_cols[1]:
    #     st.button("⭳ Export", use_container_width=True)

# ---------- Mode routing ----------
def _back_to_list():
    st.session_state.cb_mode = "list"
    st.session_state.cb_selected_id = None
    st.session_state.cb_confirm_delete_id = None

def _open_view(recipe_id):
    st.session_state.cb_selected_id = recipe_id
    st.session_state.cb_mode = "view"
    st.session_state.cb_confirm_delete_id = None

def _open_edit(recipe_id):
    st.session_state.cb_selected_id = recipe_id
    st.session_state.cb_mode = "edit"
    st.session_state.cb_confirm_delete_id = None

# ---------- Add recipe form (only when Add pressed) ----------
if st.session_state.cb_mode == "add":
    st.subheader("Add a new recipe")
    with st.form("cb_add_form", clear_on_submit=False):
        title = st.text_input("Title *", placeholder="e.g., Chicken Wings")
        ingredients = st.text_area("Ingredients", placeholder="One per line…")
        instructions = st.text_area("Instructions", placeholder="Steps…")
        submitted = st.form_submit_button("Save")
        cancel = st.form_submit_button("Cancel", type="secondary")

    if cancel:
        _back_to_list()
    elif submitted:
        if not title.strip():
            st.error("Title is required.")
        else:
            # Your add_recipe should accept at least a title; others optional.
            try:
                add_recipe(title=title.strip(), ingredients=ingredients.strip(), instructions=instructions.strip())
                st.success(f"Recipe “{title.strip()}” added.")
                _back_to_list()
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not add recipe: {e}")

# ---------- View / Edit logic ----------
elif st.session_state.cb_mode in ("view", "edit") and st.session_state.cb_selected_id is not None:
    # Load the selected recipe
    try:
        recipe = get_recipe(st.session_state.cb_selected_id)
    except Exception as e:  # noqa: BLE001
        recipe = None
        st.error(f"Failed to load recipe: {e}")

    if not recipe:
        st.info("Recipe not found. It may have been deleted.")
        _back_to_list()
    else:
        # Robustly extract fields
        rid = _get_id(recipe)
        rtitle = _normalize_title(recipe)

        def _get_field(obj, key, default=""):
            if isinstance(obj, dict):
                return obj.get(key, default) or default
            if isinstance(obj, (list, tuple)):
                # naive mapping: assume fixed positions if you use tuples; adjust as needed
                # try some common positions (title at 1, ingredients at 2, instructions at 3)
                if key == "ingredients" and len(obj) > 2: return obj[2] or default
                if key == "instructions" and len(obj) > 3: return obj[3] or default
            return default

        ringing = _get_field(recipe, "ingredients", "")
        rinstr = _get_field(recipe, "instructions", "")

        if st.session_state.cb_mode == "view":
            st.subheader(rtitle or "Untitled")
            if ringing:
                with st.expander("Ingredients", expanded=True):
                    st.markdown(f"```\n{ringing}\n```")
            if rinstr:
                with st.expander("Instructions", expanded=True):
                    st.markdown(rinstr)

            c1, c2, c3 = st.columns([1, 1, 6])
            with c1:
                if st.button("✏️ Edit", use_container_width=True):
                    _open_edit(rid)
            with c2:
                if st.button("🗑️ Remove", use_container_width=True):
                    st.session_state.cb_confirm_delete_id = rid

            if st.session_state.cb_confirm_delete_id == rid:
                st.warning("Are you sure you want to delete this recipe?")
                dc1, dc2, _ = st.columns([1, 1, 6])
                with dc1:
                    if st.button("Yes, delete", type="primary", use_container_width=True):
                        if delete_recipe is None:
                            st.error("Delete is not available yet. Please implement `delete_recipe` in food/db.py.")
                        else:
                            try:
                                delete_recipe(rid)
                                st.success("Recipe deleted.")
                                _back_to_list()
                            except Exception as e:  # noqa: BLE001
                                st.error(f"Could not delete: {e}")
                with dc2:
                    if st.button("No, cancel", use_container_width=True):
                        st.session_state.cb_confirm_delete_id = None

            st.button("← Back", on_click=_back_to_list)

        elif st.session_state.cb_mode == "edit":
            st.subheader(f"Edit: {rtitle or 'Untitled'}")
            with st.form("cb_edit_form"):
                new_title = st.text_input("Title *", value=rtitle)
                new_ing = st.text_area("Ingredients", value=ringing)
                new_instr = st.text_area("Instructions", value=rinstr)
                save = st.form_submit_button("Save changes")
                cancel = st.form_submit_button("Cancel", type="secondary")

            if cancel:
                _open_view(rid)
            elif save:
                if not new_title.strip():
                    st.error("Title is required.")
                else:
                    try:
                        update_recipe(
                            recipe_id=rid,
                            title=new_title.strip(),
                            ingredients=new_ing.strip(),
                            instructions=new_instr.strip(),
                        )
                        st.success("Recipe updated.")
                        _open_view(rid)
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Could not update: {e}")

# ---------- List mode (default) ----------
if st.session_state.cb_mode == "list":
    # Filter + sort
    filtered = _filter_by_query(all_recipes, st.session_state.cb_query)
    # Overall alphabetical sort by title
    filtered.sort(key=lambda x: _normalize_title(x).lower())

    # Group by A–Z
    buckets = _group_by_letter(filtered)

    # Render buckets
    for ch in string.ascii_uppercase:
        items = buckets[ch]
        st.markdown(f"### {ch}")
        if not items:
            # faint placeholder row to keep the vertical rhythm consistent
            st.caption("—")
        else:
            for r in items:
                title = _normalize_title(r)
                rid = _get_id(r)
                # Clickable row
                if st.button(title, key=f"row_{ch}_{rid}", use_container_width=True):
                    _open_view(rid)
        st.divider()
