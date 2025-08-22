#test

# pages/cookbook.py
import io
import html  # for safely escaping text inside HTML
import string
from typing import List, Dict, Any, Optional

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image  # for resizing uploaded images

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

    # ---- image helpers (200x200 max, preserve aspect ratio, no upscaling) ----
    def _resize_image_to_max_200(file) -> (bytes, str, str):
        """
        Resize uploaded image to max 200x200 while preserving aspect ratio (no upscaling).
        Returns (img_bytes, mime_type, original_filename).
        """
        image = Image.open(file)
        image.thumbnail((200, 200))
        buf = io.BytesIO()
        fmt = image.format or "PNG"
        image.save(buf, format=fmt)
        img_bytes = buf.getvalue()
        mime = getattr(file, "type", None) or ("image/png" if fmt and fmt.upper() == "PNG" else f"image/{(fmt or 'png').lower()}")
        name = getattr(file, "name", None) or f"image.{(fmt or 'png').lower()}"
        return img_bytes, mime, name

    def _pil_preview_200(file) -> Image.Image:
        """Return a PIL image preview resized to max 200x200 (no upscaling)."""
        im = Image.open(file).copy()
        im.thumbnail((200, 200))
        return im

    # ---------- servings helper ----------
    def _extract_servings(rec: Any) -> Optional[int]:
        """
        Try to read 'servings' from the recipe dict using several possible keys.
        Returns an int if found and > 0, else None.
        """
        if not isinstance(rec, dict):
            return None
        candidates = [
            "servings", "serve", "serves", "people", "num_people",
            "portion", "portions", "servings_count"
        ]
        for k in candidates:
            if k in rec and rec[k] is not None and str(rec[k]).strip() != "":
                try:
                    val = int(str(rec[k]).strip())
                    if val > 0:
                        return val
                except Exception:
                    pass
        return None

    # ---------- ingredients helpers ----------
    def _rows_from_text(ingredients_text: str) -> List[Dict[str, str]]:
        """
        Parse ingredients from stored text.
        Expected saved format (TSV-like): 'name<TAB>amount<TAB>unit' per line.
        Backwards compatible with older free-form text: produce one row with 'name' as the whole line.
        """
        rows: List[Dict[str, str]] = []
        text = (ingredients_text or "").strip()
        if not text:
            return rows
        lines = text.splitlines()
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 3:
                name = parts[0].strip()
                amount = parts[1].strip()
                unit = parts[2].strip()
                if name or amount or unit:
                    rows.append({"name": name, "amount": amount, "unit": unit})
            else:
                name = line.strip()
                if name:
                    rows.append({"name": name, "amount": "", "unit": ""})
        return rows

    def _text_from_rows(rows: List[Dict[str, str]]) -> str:
        """
        Build TSV-like text from ingredient rows: 'name<TAB>amount<TAB>unit' per line.
        Empty-name rows are ignored.
        """
        out_lines = []
        for r in rows:
            name = (r.get("name") or "").strip()
            amount = (r.get("amount") or "").strip()
            unit = (r.get("unit") or "").strip()
            if name:  # only keep rows with a name
                out_lines.append(f"{name}\t{amount}\t{unit}")
        return "\n".join(out_lines)

    def _render_ingredients_preview(ingredients_text: str):
        """
        Render ingredients as a clean bullet list in preview mode.
        Uses parsed rows; falls back to raw text if nothing parses.
        """
        rows = _rows_from_text(ingredients_text)
        if rows:
            bullets = []
            for r in rows:
                name = r.get("name", "").strip()
                amount = r.get("amount", "").strip()
                unit = r.get("unit", "").strip()
                suffix = ""
                if amount and unit:
                    suffix = f" — {amount} {unit}"
                elif amount:
                    suffix = f" — {amount}"
                elif unit:
                    suffix = f" — {unit}"
                safe_line = html.escape(f"{name}{suffix}")
                bullets.append(f"- {safe_line}")
            st.markdown("**Ingredients**")
            st.markdown("\n".join(bullets))
        else:
            txt = (ingredients_text or "").strip()
            if txt:
                st.markdown("**Ingredients**")
                safe = html.escape(txt).replace("\n", "<br>")
                st.markdown(f"<div>{safe}</div>", unsafe_allow_html=True)

    def _ingredients_table_editor(state_key_prefix: str) -> List[Dict[str, str]]:
        """
        Render a table-like editor for ingredients using Streamlit inputs.
        Returns the updated list of rows from the current widget values.
        Uses st.session_state to persist between reruns.
        """
        # Ensure list exists in session
        if f"{state_key_prefix}_rows" not in st.session_state:
            st.session_state[f"{state_key_prefix}_rows"] = [{"name": "", "amount": "", "unit": ""}]

        rows: List[Dict[str, str]] = st.session_state[f"{state_key_prefix}_rows"]

        st.markdown("**Ingredients**")

        # Header
        hc1, hc2, hc3, hc4, hc5 = st.columns([0.3, 3.0, 1.2, 1.2, 0.7])
        with hc1:
            st.markdown("**•**")
        with hc2:
            st.markdown("**Name**")
        with hc3:
            st.markdown("**Amount**")
        with hc4:
            st.markdown("**Unit**")
        with hc5:
            st.markdown(" ")  # spacer for delete column

        # Collect updates
        updated_rows: List[Dict[str, str]] = []
        delete_index = None

        for i, r in enumerate(rows):
            c1, c2, c3, c4, c5 = st.columns([0.3, 3.0, 1.2, 1.2, 0.7])
            with c1:
                st.markdown("•")
            with c2:
                name = st.text_input(
                    label=f"Name {i}",
                    value=r.get("name", ""),
                    key=f"{state_key_prefix}_name_{i}",
                    label_visibility="collapsed",
                    placeholder="e.g., Flour",
                )
            with c3:
                amount = st.text_input(
                    label=f"Amount {i}",
                    value=r.get("amount", ""),
                    key=f"{state_key_prefix}_amt_{i}",
                    label_visibility="collapsed",
                    placeholder="e.g., 200",
                )
            with c4:
                unit = st.text_input(
                    label=f"Unit {i}",
                    value=r.get("unit", ""),
                    key=f"{state_key_prefix}_unit_{i}",
                    label_visibility="collapsed",
                    placeholder="e.g., g",
                )
            with c5:
                if st.button("✖", key=f"{state_key_prefix}_del_{i}", help="Delete this row"):
                    delete_index = i
            updated_rows.append({"name": name, "amount": amount, "unit": unit})

        # Row deletion
        if delete_index is not None:
            if 0 <= delete_index < len(updated_rows):
                updated_rows.pop(delete_index)
                if not updated_rows:
                    updated_rows = [{"name": "", "amount": "", "unit": ""}]
            st.session_state[f"{state_key_prefix}_rows"] = updated_rows
            st.rerun()

        # Add row button
        if st.button("➕ Add row", key=f"{state_key_prefix}_addrow"):
            updated_rows.append({"name": "", "amount": "", "unit": ""})
            st.session_state[f"{state_key_prefix}_rows"] = updated_rows
            st.rerun()

        # Persist latest values
        st.session_state[f"{state_key_prefix}_rows"] = updated_rows
        return updated_rows

    # Render multi-line plain text with preserved newlines + nice spacing
    def _render_multiline(label: str, text: str, top_margin: str = "1rem"):
        txt = (text or "").strip()
        if not txt:
            return
        safe_label = html.escape(label)
        safe_text = html.escape(txt)
        st.markdown(
            f"""
            <div style="margin-top:{top_margin};">
              <div style="font-weight:600; margin-bottom:0.35rem;">{safe_label}</div>
              <div style="white-space:pre-wrap;">{safe_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Autosize helper for text_area rows
    def _auto_rows(current_text: str, base: int = 6, max_rows: int = 24) -> int:
        lines = max(1, (current_text or "").count("\n") + 1)
        return max(base, min(lines + 1, max_rows))

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
        # reset ingredients editor state
        st.session_state.pop("add_ing_rows", None)
        # reset add instructions state
        st.session_state.pop("add_instructions", None)

    def _back_to_list():
        ss.cb_mode = "list"
        ss.cb_selected_id = None
        ss.cb_confirm_delete_id = None

    def _select(recipe_id: int):
        ss.cb_selected_id = recipe_id
        ss.cb_mode = "view"
        ss.cb_confirm_delete_id = None

    def _edit(recipe_id: int):
        ss.cb_selected_id = recipe_id
        ss.cb_mode = "edit"
        ss.cb_confirm_delete_id = None
        # reset editor; will initialize from recipe on render
        st.session_state.pop("edit_ing_rows", None)
        st.session_state.pop("edit_instructions", None)

    # ---------- header ----------
    st.header("Cook Book", divider="gray")
    total = count_recipes()
    st.caption(f"You have **{total}** recipe{'s' if total != 1 else ''} in your cook book.")

    # ========== ADD PAGE ==========
    if ss.cb_mode == "add":
        st.subheader("Add a new recipe")

        # Initialize ingredients editor storage for Add
        if "add_ing_rows" not in st.session_state:
            st.session_state["add_ing_rows"] = [{"name": "", "amount": "", "unit": ""}]

        # Title
        title = st.text_input("Title *", placeholder="e.g., Chicken Wings")

        # Servings (required)
        servings_options = list(range(1, 21))  # 1..20
        servings_idx_default = 1  # default to "2"
        sev = st.selectbox(
            "For how many people is this recipe served? *",
            servings_options,
            index=servings_idx_default,
            help="This is used for later shopping list calculations.",
            key="add_servings",
        )
        servings_val = int(sev) if sev else None

        # Image (with preview)
        uploaded_img = st.file_uploader(
            "Recipe image (optional)",
            type=["png", "jpg", "jpeg", "webp"],
            help="Add a photo for this recipe."
        )
        if uploaded_img is not None:
            try:
                preview_im = _pil_preview_200(uploaded_img)
                st.image(preview_im, caption="Selected image (preview)")
            except Exception:
                st.warning("Could not preview this image format, but it will still be saved after resizing.")

        # Ingredients table editor
        add_rows = _ingredients_table_editor("add_ing")

        # Instructions (auto-sized)
        current_add_instr = st.session_state.get("add_instructions", "")
        add_instr_rows = _auto_rows(current_add_instr)
        instructions = st.text_area(
            "Instructions",
            value=current_add_instr,
            key="add_instructions",
            placeholder="Steps…",
            help="This box grows with your text for easier reading.",
            height=None,
            max_chars=None,
            label_visibility="visible",
            disabled=False,
        )
        st.markdown(
            f"<style>.stTextArea textarea{{min-height:{add_instr_rows * 24}px;}}</style>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Save", use_container_width=True, key="add_save_btn"):
                if not title.strip():
                    st.error("Title is required.")
                elif not servings_val:
                    st.error("Please select how many people this recipe serves.")
                else:
                    try:
                        img_bytes = img_mime = img_name = None
                        if uploaded_img is not None:
                            img_bytes, img_mime, img_name = _resize_image_to_max_200(uploaded_img)

                        ingredients_text = _text_from_rows(add_rows)

                        # Try to store servings if DB supports it
                        try:
                            add_recipe(
                                title=title.strip(),
                                ingredients=ingredients_text,
                                instructions=instructions.strip(),
                                image_bytes=img_bytes,
                                image_mime=img_mime,
                                image_filename=img_name,
                                servings=int(servings_val),
                            )
                        except TypeError:
                            # Fallback: call without servings if the DB API doesn't accept it
                            add_recipe(
                                title=title.strip(),
                                ingredients=ingredients_text,
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
        with c2:
            if st.button("Cancel", use_container_width=True, key="add_cancel_btn"):
                _back_to_list()
                st.rerun()

        return  # Add page shows nothing else

    # ========== VIEW PAGE (preview: big bold title + image + text, no inputs) ==========
    if ss.cb_mode == "view":
        recipe = None
        if ss.cb_selected_id is not None:
            try:
                recipe = get_recipe(ss.cb_selected_id)
            except Exception as e:
                st.error(f"Failed to load recipe: {e}")

        if not recipe:
            st.info("Recipe not found. It may have been deleted.")
            _back_to_list()
            st.rerun()
            return

        rid = _get_id(recipe)
        rtitle = _normalize_title(recipe) or "Untitled"
        rimg = recipe.get("image_bytes") if isinstance(recipe, dict) else None
        ringing = recipe.get("ingredients", "") if isinstance(recipe, dict) else ""
        rinstr = recipe.get("instructions", "") if isinstance(recipe, dict) else ""
        rserv = _extract_servings(recipe)

        # Title only: bold + larger font
        safe_title = html.escape(rtitle)
        st.markdown(
            f"""
            <div style="font-weight: 800; font-size: 1.8rem; line-height: 1.2; margin-bottom: 1rem;">
              {safe_title}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Image
        if rimg:
            st.image(rimg, caption=None)
        else:
            st.caption("No image uploaded.")

        # Servings sentence directly UNDER the image (always check and show if available)
        if rserv is not None:
            st.markdown(f"**Serves for {rserv} {'people' if rserv != 1 else 'person'}.**")

        # Ingredients as bullet list
        _render_ingredients_preview(ringing)

        # Instructions plain text (if any)
        if (rinstr or "").strip():
            _render_multiline("Instructions", rinstr, top_margin="1.2rem")

        st.divider()

        # Actions
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("✏️ Edit", use_container_width=True, key="view_edit_btn"):
                _edit(rid)
                st.rerun()
        with c2:
            if st.button("🗑️ Remove", use_container_width=True, key="view_remove_btn"):
                ss.cb_confirm_delete_id = rid
        with c3:
            if st.button("← Back to list", use_container_width=True, key="back_to_list_btn"):
                _back_to_list()
                st.rerun()

        # Delete confirmation
        if ss.cb_confirm_delete_id == rid:
            st.warning("Are you sure you want to delete this recipe?")
            dc1, dc2 = st.columns([1, 1])
            with dc1:
                if st.button("Yes, delete", type="primary", use_container_width=True, key="confirm_delete_yes"):
                    try:
                        delete_recipe(rid)
                        st.toast("Recipe deleted.", icon="🗑️")
                        _back_to_list()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not delete: {e}")
            with dc2:
                if st.button("No, cancel", use_container_width=True, key="confirm_delete_no"):
                    ss.cb_confirm_delete_id = None
                    st.rerun()
        return  # View page done

    # ========== EDIT PAGE (table editor visible here) ==========
    if ss.cb_mode == "edit":
        recipe = None
        if ss.cb_selected_id is not None:
            try:
                recipe = get_recipe(ss.cb_selected_id)
            except Exception as e:
                st.error(f"Failed to load recipe: {e}")

        if not recipe:
            st.info("Recipe not found. It may have been deleted.")
            _back_to_list()
            st.rerun()
            return

        rid = _get_id(recipe)
        rtitle = _normalize_title(recipe)
        orig_ing_text = recipe.get("ingredients", "") if isinstance(recipe, dict) else ""
        rimg = recipe.get("image_bytes") if isinstance(recipe, dict) else None
        rinstr = recipe.get("instructions", "") if isinstance(recipe, dict) else ""
        rserv = _extract_servings(recipe) or 2  # default selection if missing

        st.subheader(f"Edit: {rtitle or 'Untitled'}")

        # Initialize editor rows for edit mode once per recipe
        if "edit_ing_rows" not in st.session_state:
            st.session_state["edit_ing_rows"] = _rows_from_text(orig_ing_text) or [{"name": "", "amount": "", "unit": ""}]

        # Title
        new_title = st.text_input("Title *", value=rtitle or "")

        # Servings (required)
        servings_options = list(range(1, 21))
        start_idx = servings_options.index(rserv) if rserv in servings_options else 1
        new_servings = st.selectbox(
            "For how many people is this recipe served? *",
            servings_options,
            index=start_idx,
            help="This is used for later shopping list calculations.",
            key="edit_servings",
        )

        # Image uploader
        e_uploaded = st.file_uploader(
            "Change or add image (optional)",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload to replace/add an image."
        )

        if rimg and e_uploaded is None:
            st.image(rimg, caption="Current image")

        if e_uploaded is not None:
            try:
                preview_im = _pil_preview_200(e_uploaded)
                st.image(preview_im, caption="New image (preview)")
            except Exception:
                st.warning("Could not preview this image format, but it will still be saved after resizing.")

        # Ingredients table editor
        edit_rows = _ingredients_table_editor("edit_ing")

        # Instructions (auto-sized)
        current_edit_instr = st.session_state.get("edit_instructions", rinstr or "")
        edit_instr_rows = _auto_rows(current_edit_instr)
        new_instr = st.text_area(
            "Instructions",
            value=current_edit_instr,
            key="edit_instructions",
            height=None,
            help="This box grows with your text for easier reading.",
        )
        st.markdown(
            f"<style>.stTextArea textarea{{min-height:{edit_instr_rows * 24}px;}}</style>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Save changes", use_container_width=True, key="edit_save_btn"):
                if not new_title.strip():
                    st.error("Title is required.")
                elif not new_servings:
                    st.error("Please select how many people this recipe serves.")
                else:
                    try:
                        replace = e_uploaded is not None
                        img_bytes = img_mime = img_name = None
                        if replace:
                            img_bytes, img_mime, img_name = _resize_image_to_max_200(e_uploaded)

                        ingredients_text = _text_from_rows(edit_rows)

                        # Try to update with servings; fallback without if API doesn't support it
                        try:
                            update_recipe(
                                recipe_id=rid,
                                title=new_title.strip(),
                                ingredients=ingredients_text,
                                instructions=new_instr.strip(),
                                image_bytes=img_bytes if replace else None,
                                image_mime=img_mime if replace else None,
                                image_filename=img_name if replace else None,
                                keep_existing_image=not replace,
                                servings=int(new_servings),
                            )
                        except TypeError:
                            update_recipe(
                                recipe_id=rid,
                                title=new_title.strip(),
                                ingredients=ingredients_text,
                                instructions=new_instr.strip(),
                                image_bytes=img_bytes if replace else None,
                                image_mime=img_mime if replace else None,
                                image_filename=img_name if replace else None,
                                keep_existing_image=not replace,
                            )

                        st.toast("Recipe updated.", icon="✏️")
                        ss.cb_mode = "view"
                        # clear edit table state after save
                        st.session_state.pop("edit_ing_rows", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update: {e}")
        with c2:
            if st.button("Cancel", use_container_width=True, key="edit_cancel_btn"):
                ss.cb_mode = "view"
                # clear edit table state on cancel
                st.session_state.pop("edit_ing_rows", None)
                st.rerun()

        return  # Edit page done

    # ========== LIST PAGE (default) ==========
    if ss.cb_mode == "list":
        left, _ = st.columns([2.2, 3])

        with left:
            ss.cb_query = st.text_input(
                "",
                value=ss.cb_query,
                placeholder="Start typing… then press Enter to apply",
                key="cb_query_input",
                label_visibility="collapsed",
            )

            # Tight spacing (search → button → first header)
            st.markdown(
                """
                <style>
                  div[data-testid="stTextInput"] { margin-bottom: 0.2rem !important; }
                  div[data-testid="stButton"]    { margin-bottom: 0.2rem !important; }
                  div[data-testid="stMarkdown"] h3 {
                      margin-top: 0.2rem !important;
                      margin-bottom: 0.2rem !important;
                  }
                </style>
                """,
                unsafe_allow_html=True,
            )

            if st.button("➕ Add recipe", use_container_width=True):
                _open_add()
                st.rerun()

            # Prevent Enter from navigating away
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
                        if st.button(title, key=f"row_{ch}_{rid}", use_container_width=True):
                            _select(rid)
                            st.rerun()
                st.divider()

        # Auto-scroll to first typed character
        q = (st.session_state.cb_query or "").strip()
        if q and q[0].isalpha():
            first_letter = q[0].upper()
            components.html(
                f"""
                <script>
                  const doc = window.parent.document;
                  const el = document.getElementById('sec-{first_letter}');
                  if (el) {{
                    el.scrollIntoView({{behavior: 'instant', block: 'start'}});
                  }}
                </script>
                """,
                height=0,
            )
