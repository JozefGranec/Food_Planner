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
        ss.cb_mode = "list"  # "list" | "add" | "view" | "edit"
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

            # Image upload right under instructions
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
        return  # Add page shows nothing else

    # ========== LIST (always A–Z) + RIGHT PANEL ==========
    left, right = st.columns([2.2, 3])

    with left:
        # --- Search: show only placeholder text; reduce spacing below field ---
        ss.cb_query = st.text_input(
            "",  # empty label
            value=ss.cb_query,
            placeholder="Start typing… then press Enter to apply",
            key="cb_query_input",
            label_visibility="collapsed",
        )

        # Tighten spacing below the search input
        st.markdown(
            """
            <style>
            /* Reduce bottom margin under the FIRST text input in the left column */
            div[data-testid="stTextInput"] {
                margin-bottom: 0.25rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Keep the Add button close to the search
        if st.button("➕ Add recipe", use_container_width=True):
            _open_add()
            st.rerun()

        # Keep the Add button close to the A–Z list
if st.button("➕ Add recipe", use_container_width=True):
    _open_add()
    st.rerun()

# ↓ Kill extra spacing between Add button and the first "A" header
st.markdown(
    """
    <style>
    /* Remove bottom margin under buttons */
    div[data-testid="stButton"] { margin-bottom: 0rem !important; }
    /* Remove top margin on markdown h3 headers (### A, B, C...) */
    div[data-testid="stMarkdown"] h3 { margin-top: 0rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

        # Prevent Enter from navigating to other pages + keep focus in app
        # Use placeholder selector (robust when label is collapsed)
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

        # Build filtered A–Z list
        all_recipes: List[Any] = list_recipes() or []
        all_recipes.sort(key=lambda x: _normalize_title(x).lower())
        filtered = _filter_by_query(all_recipes, ss.cb_query)
        buckets = _group_by_letter(filtered)

        # ALWAYS render A–Z with anchors, even when empty
        for ch in string.ascii_uppercase:
            st.markdown(f"<a id='sec-{ch}'></a>", unsafe_allow_html=True)  # anchor
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
        if ss.cb_selected_id is None:
            st.caption("Select a recipe on the left to view / edit it.")
        else:
            try:
                recipe = get_recipe(ss.cb_selected_id)
            except Exception as e:
                recipe = None
                st.error(f"Failed to load recipe: {e}")

            if not recipe:
                st.info("Recipe not found. It may have been deleted.")
                ss.cb_selected_id = None
                st.rerun()

            rid = _get_id(recipe)
            rtitle = _normalize_title(recipe)
            ringing = recipe.get("ingredients", "") if isinstance(recipe, dict) else ""
            rinstr = recipe.get("instructions", "") if isinstance(recipe, dict) else ""
            rimg = recipe.get("image_bytes") if isinstance(recipe, dict) else None

            if ss.cb_mode == "view":
                st.subheader(rtitle or "Untitled")

                if rimg:
                    st.image(rimg, caption=rtitle or "Recipe image", use_container_width=True)

                if ringing:
                    with st.expander("Ingredients", expanded=True):
                        st.markdown(f"```\n{ringing}\n```")
                if rinstr:
                    with st.expander("Instructions", expanded=True):
                        st.markdown(rinstr)

                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button("✏️ Edit", use_container_width=True):
                        _edit(rid)
                        st.rerun()
                with c2:
                    if st.button("🗑️ Remove", use_container_width=True):
                        ss.cb_confirm_delete_id = rid
                with c3:
                    if st.button("↩︎ Deselect", use_container_width=True):
                        ss.cb_selected_id = None
                        st.rerun()

                if ss.cb_confirm_delete_id == rid:
                    st.warning("Are you sure you want to delete this recipe?")
                    dc1, dc2 = st.columns([1, 1])
                    with dc1:
                        if st.button("Yes, delete", type="primary", use_container_width=True):
                            try:
                                delete_recipe(rid)
                                st.toast("Recipe deleted.", icon="🗑️")
                                ss.cb_selected_id = None
                                ss.cb_confirm_delete_id = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not delete: {e}")
                    with dc2:
                        if st.button("No, cancel", use_container_width=True):
                            ss.cb_confirm_delete_id = None
                            st.rerun()

            elif ss.cb_mode == "edit":
                st.subheader(f"Edit: {rtitle or 'Untitled'}")
                with st.form("cb_edit_form"):
                    new_title = st.text_input("Title *", value=rtitle)
                    new_ing = st.text_area("Ingredients", value=ringing)
                    new_instr = st.text_area("Instructions", value=rinstr)

                    if rimg:
                        st.image(rimg, caption="Current image", use_container_width=True)

                    e_uploaded = st.file_uploader(
                        "Replace image (optional)",
                        type=["png", "jpg", "jpeg", "webp"],
                        help="Upload to replace or add an image. Leave empty to keep current."
                    )

                    c1, c2 = st.columns([1, 1])
                    with c1:
                        save = st.form_submit_button("Save changes", use_container_width=True)
                    with c2:
                        cancel = st.form_submit_button("Cancel", type="secondary", use_container_width=True)

                if cancel:
                    ss.cb_mode = "view"
                    st.rerun()

                if save:
                    if not new_title.strip():
                        st.error("Title is required.")
                    else:
                        try:
                            replace = e_uploaded is not None
                            img_bytes = img_mime = img_name = None
                            if replace:
                                img_bytes = e_uploaded.getvalue()
                                img_mime = e_uploaded.type
                                img_name = e_uploaded.name

                            update_recipe(
                                recipe_id=rid,
                                title=new_title.strip(),
                                ingredients=new_ing.strip(),
                                instructions=new_instr.strip(),
                                image_bytes=img_bytes if replace else None,
                                image_mime=img_mime if replace else None,
                                image_filename=img_name if replace else None,
                                keep_existing_image=not replace,
                            )
                            st.toast("Recipe updated.", icon="✏️")
                            ss.cb_mode = "view"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not update: {e}")

    # ===== AUTO-SCROLL to first typed character (even if no results under that letter) =====
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
