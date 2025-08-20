# pages/cookbook.py
import streamlit as st
import string
from typing import List, Dict, Any, Optional

from food.db import (
    init_db,
    add_recipe,
    list_recipes,
    get_recipe,
    update_recipe,
    delete_recipe,
    count_recipes,
)

def render():
    init_db()

    # ---------- utilities ----------
    def _normalize_title(r: Any) -> str:
        if isinstance(r, dict):
            return str(r.get("title") or r.get("name") or r.get("Title") or "")
        if isinstance(r, (list, tuple)):
            return str(r[1]) if len(r) > 1 else str(r[0])
        return str(r)

    def _get_id(r: Any) -> Any:
        if isinstance(r, dict):
            return r.get("id") or r.get("recipe_id") or r.get("ID")
        if isinstance(r, (list, tuple)):
            return r[0]
        return None

    def _group_by_letter(recipes: List[Any]) -> Dict[str, List[Any]]:
        buckets: Dict[str, List[Any]] = {ch: [] for ch in string.ascii_uppercase}
        for r in recipes:
            t = _normalize_title(r).strip()
            if not t:
                continue
            first = t[0].upper()
            key = first if first in buckets else "Z"
            buckets[key].append(r)
        for k in buckets:
            buckets[k].sort(key=lambda x: _normalize_title(x).lower())
        return buckets

    def _filter_by_query(recipes: List[Any], q: str) -> List[Any]:
        q = q.strip().lower()
        if not q:
            return recipes
        return [r for r in recipes if q in _normalize_title(r).lower()]

    # ---------- session ----------
    if "cb_selected_id" not in st.session_state:
        st.session_state.cb_selected_id = None
    if "cb_mode" not in st.session_state:
        st.session_state.cb_mode = "list"  # "list" | "view" | "edit" | "add"
    if "cb_confirm_delete_id" not in st.session_state:
        st.session_state.cb_confirm_delete_id = None
    if "cb_query" not in st.session_state:
        st.session_state.cb_query = ""

    # ---------- UI ----------
    st.header("Cook Book", divider="gray")

    total = count_recipes()
    st.caption(f"You have **{total}** recipe{'s' if total != 1 else ''} in your cook book.")

    left, right = st.columns([3, 2])
    with left:
        st.session_state.cb_query = st.text_input(
            "Search recipes",
            value=st.session_state.cb_query,
            placeholder="Start typing… e.g., 'chi' for 'Chicken'",
        )
    with right:
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            if st.button("➕ Add recipe", use_container_width=True):
                st.session_state.cb_mode = "add"
                st.session_state.cb_selected_id = None
                st.session_state.cb_confirm_delete_id = None

    # helpers
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

    # ---------- add ----------
    if st.session_state.cb_mode == "add":
        st.subheader("Add a new recipe")
        with st.form("cb_add_form", clear_on_submit=False):
            title = st.text_input("Title *", placeholder="e.g., Chicken Wings")
            ingredients = st.text_area("Ingredients", placeholder="One per line…")
            instructions = st.text_area("Instructions", placeholder="Steps…")
            save = st.form_submit_button("Save")
            cancel = st.form_submit_button("Cancel", type="secondary")

        if cancel:
            _back_to_list()
            st.rerun()

        if save:
            if not title.strip():
                st.error("Title is required.")
            else:
                try:
                    add_recipe(
                        title=title.strip(),
                        ingredients=ingredients.strip(),
                        instructions=instructions.strip(),
                    )
                    st.toast(f"Recipe “{title.strip()}” added.", icon="✅")
                    _back_to_list()
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not add recipe: {e}")

    # ---------- view / edit ----------
    elif st.session_state.cb_mode in ("view", "edit") and st.session_state.cb_selected_id is not None:
        try:
            recipe = get_recipe(st.session_state.cb_selected_id)
        except Exception as e:
            recipe = None
            st.error(f"Failed to load recipe: {e}")

        if not recipe:
            st.info("Recipe not found. It may have been deleted.")
            _back_to_list()
            st.rerun()

        rid = _get_id(recipe)
        rtitle = _normalize_title(recipe)
        ringing = recipe.get("ingredients", "") if isinstance(recipe, dict) else ""
        rinstr = recipe.get("instructions", "") if isinstance(recipe, dict) else ""

        if st.session_state.cb_mode == "view":
            st.subheader(rtitle or "Untitled")
            if ringing:
                with st.expander("Ingredients", expanded=True):
                    st.markdown(f"```\n{ringing}\n```")
            if rinstr:
                with st.expander("Instructions", expanded=True):
                    st.markdown(rinstr)

            b1, b2, _ = st.columns([1, 1, 6])
            with b1:
                if st.button("✏️ Edit", use_container_width=True):
                    _open_edit(rid)
                    st.rerun()
            with b2:
                if st.button("🗑️ Remove", use_container_width=True):
                    st.session_state.cb_confirm_delete_id = rid

            if st.session_state.cb_confirm_delete_id == rid:
                st.warning("Are you sure you want to delete this recipe?")
                dc1, dc2, _ = st.columns([1, 1, 6])
                with dc1:
                    if st.button("Yes, delete", type="primary", use_container_width=True):
                        try:
                            delete_recipe(rid)
                            st.toast("Recipe deleted.", icon="🗑️")
                            _back_to_list()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not delete: {e}")
                with dc2:
                    if st.button("No, cancel", use_container_width=True):
                        st.session_state.cb_confirm_delete_id = None
                        st.rerun()

            if st.button("← Back"):
                _back_to_list()
                st.rerun()

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
                st.rerun()

            if save:
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
                        st.toast("Recipe updated.", icon="✏️")
                        _open_view(rid)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update: {e}")

    # ---------- list ----------
    if st.session_state.cb_mode == "list":
        all_recipes: List[Any] = list_recipes() or []
        all_recipes.sort(key=lambda x: _normalize_title(x).lower())
        filtered = _filter_by_query(all_recipes, st.session_state.cb_query)
        buckets = _group_by_letter(filtered)

        for ch in string.ascii_uppercase:
            items = buckets[ch]
            st.markdown(f"### {ch}")
            if not items:
                st.caption("—")
            else:
                for r in items:
                    title = _normalize_title(r)
                    rid = _get_id(r)
                    if st.button(title, key=f"row_{ch}_{rid}", use_container_width=True):
                        _open_view(rid)
                        st.rerun()
            st.divider()
