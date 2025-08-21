# pages/cookbook.py
import streamlit as st
import streamlit.components.v1 as components
import string
from typing import List, Dict, Any

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
            return str(r.get("title") or "")
        if isinstance(r, (list, tuple)):
            return str(r[1]) if len(r) > 1 else str(r[0])
        return str(r)

    def _get_id(r: Any) -> Any:
        if isinstance(r, dict):
            return r.get("id")
        if isinstance(r, (list, tuple)):
            return r[0]
        return None

    def _filter_by_query(recipes: List[Any], q: str) -> List[Any]:
        q = (q or "").strip().lower()
        if not q:
            return recipes
        return [r for r in recipes if q in _normalize_title(r).lower()]

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

    # ---------- session ----------
    ss = st.session_state
    if "cb_mode" not in ss:
        ss.cb_mode = "list"
    if "cb_selected_id" not in ss:
        ss.cb_selected_id = None
    if "cb_query" not in ss:
        ss.cb_query = ""
    if "cb_confirm_delete_id" not in ss:
        ss.cb_confirm_delete_id = None

    # helpers
    def _open_add():
        ss.cb_mode = "add"
        ss.cb_selected_id = None
        ss.cb_confirm_delete_id = None

    def _back_to_list():
        ss.cb_mode = "list"
        ss.cb_confirm_delete_id = None

    def _select(recipe_id: int):
        ss.cb_selected_id = recipe_id
        ss.cb_mode = "view"
        ss.cb_confirm_delete_id = None

    def _edit(recipe_id: int):
        ss.cb_selected_id = recipe_id
        ss.cb_mode = "edit"
        ss.cb_confirm_delete_id = None

    # ---------- header ----------
    st.header("Cook Book", divider="gray")
    total = count_recipes()
    st.caption(f"You have **{total}** recipe{'s' if total != 1 else ''} in your cook book.")

    # ========== ADD PAGE ==========
    if ss.cb_mode == "add":
        st.subheader("Add a new recipe")
        with st.form("cb_add_form", clear_on_submit=False):
            title = st.text_input("Title *", placeholder="e.g., Chicken Wings")
            ingredients = st.text_area("Ingredients", placeholder="One per line…")
            instructions = st.text_area("Instructions", placeholder="Steps…")

            uploaded_img = st.file_uploader(
                "Recipe image (optional)",
                type=["png", "jpg", "jpeg", "webp"],
                help="Upload a photo for this recipe."
            )

            c1, c2 = st.columns([1, 1])
            with c1:
                save = st.form_submit_button("Save", use_container_width=True)
            with c2:
                cancel = st.form_submit_button("Cancel", type="secondary", use_container_width=True)

        if cancel:
            _back_to_list()
            st.rerun()

        if save:
            if not title.strip():
                st.error("Title is required.")
            else:
                try:
                    img_bytes = img_mime = img_name = None
                    if uploaded_img is not None:
                        img_bytes = uploaded_img.getvalue()
                        img_mime = uploaded_img.type
                        img_name = uploaded_img.name

                    add_recipe(
                        title=title.strip(),
                        ingredients=ingredients.strip(),
                        instructions=instructions.strip(),
                        image_bytes=img_bytes,
                        image_mime=img_mime,
                        image_filename=img_name,
                    )
                    st.toast(f"Recipe “{title.strip()}” added.", icon="✅")
                    _back_to_list()
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not add recipe: {e}")
        return

    # ========== LIST ==========
    left, right = st.columns([2.2, 3])

    with left:
        ss.cb_query = st.text_input(
            "",
            value=ss.cb_query,
            placeholder="Start typing… then press Enter to apply",
            key="cb_query_input",
            label_visibility="collapsed",
        )

        # 🔹 Reduce spacing under search and button, bring letter headers closer
        st.markdown(
            """
            <style>
            div[data-testid="stTextInput"] {margin-bottom: 0.25rem;}
            button[kind="secondary"] {margin-bottom: 0.25rem !important;}
            button[kind="primary"] {margin-bottom: 0.25rem !important;}
            h3 {margin-top: 0.5rem !important;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        if st.button("➕ Add recipe", use_container_width=True):
            _open_add()
            st.rerun()

        components.html(
            """
            <script>
              (function(){
                const doc = window.parent.document;
                const target = doc.querySelector('input[placeholder="Start typing… then press Enter to apply"]')
                              || doc.querySelector('input[aria-label=""]')
                              || doc.querySelector('input[type="text"]');
                if (target) {
                  target.addEventListener('keydown', function(e){
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      e.stopPropagation();
                      return false;
                    }
                  }, {capture: true});
                }
              })();
            </script>
            """,
            height=0,
        )

        all_recipes: List[Any] = list_recipes() or []
        all_recipes.sort(key=lambda x: _normalize_title(x).lower())
        filtered = _filter_by_query(all_recipes, ss.cb_query)
        buckets = _group_by_letter(filtered)

        for ch in string.ascii_uppercase:
            st.markdown(f"<a id='sec-{ch}'></a>", unsafe_allow_html=True)
            st.markdown(f"### {ch}")
            items = buckets.get(ch, [])
            if not items:
                st.caption("—")
            else:
                for r in items:
                    title = _normalize_title(r)
                    rid = _get_id(r)
                    is_selected = (ss.cb_selected_id == rid)
                    label = f"🔸 {title}" if is_selected else title
                    if st.button(label, key=f"row_{ch}_{rid}", use_container_width=True):
                        _select(rid)
                        st.rerun()
            st.divider()

    with right:
        # unchanged (recipe detail panel) ...
        # [code omitted for brevity; identical to your version]
        pass

    # ===== AUTO-SCROLL =====
    q = (st.session_state.cb_query or "").strip()
    if q and q[0].isalpha():
        first_letter = q[0].upper()
        components.html(
            f"""
            <script>
              const doc = window.parent.document;
              const el = doc.getElementById('sec-{first_letter}');
              if (el) {{
                el.scrollIntoView({{behavior: 'instant', block: 'start'}});
              }}
            </script>
            """,
            height=0,
        )
