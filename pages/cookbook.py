# pages/cookbook.py
#test
import io
import html  # for safely escaping text inside HTML
import string
from typing import List, Dict, Any, Tuple, Optional

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont  # image helpers

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
    # ---------------- DB backend selection (Postgres via Secrets or local SQLite) ----------------
    def _init_backend():
        """
        Tries to initialize DB with Streamlit Secrets (Postgres) first.
        Falls back to local SQLite file 'food.sqlite3'.
        Works with old/new init_db signatures:
          - init_db()
          - init_db(db_url="postgresql+psycopg2://...") or init_db(db_path="food.sqlite3")
          - init_db(**kwargs) where kwargs describe connection parts
        """
        # 1) Try Streamlit secrets → Postgres
        db_secrets: Optional[dict] = None
        try:
            if "database" in st.secrets:
                db_secrets = dict(st.secrets["database"])
        except Exception:
            db_secrets = None

        # Helper: build a URL if only parts are provided
        def _build_pg_url(parts: dict) -> Optional[str]:
            # Accept either "url" directly or components
            if "url" in parts and parts["url"]:
                return str(parts["url"])
            user = parts.get("user") or parts.get("username")
            pwd = parts.get("password")
            host = parts.get("host", "localhost")
            port = parts.get("port", 5432)
            dbname = parts.get("dbname") or parts.get("database")
            sslmode = parts.get("sslmode")  # optional
            if not (user and pwd and dbname):
                return None
            # Prefer SQLAlchemy scheme if your db layer supports it; still safe to pass to many libs
            base = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}"
            if sslmode:
                base += f"?sslmode={sslmode}"
            return base

        # Try Postgres first
        if db_secrets:
            pg_url = _build_pg_url(db_secrets)
            if pg_url:
                try:
                    # Preferred: URL-style
                    init_db(db_url=pg_url)
                    return
                except TypeError:
                    # Maybe it expects generic "url"
                    try:
                        init_db(url=pg_url)
                        return
                    except TypeError:
                        # Maybe it expects separate parts
                        try:
                            init_db(**db_secrets)
                            return
                        except TypeError:
                            pass
                except Exception:
                    # If URL attempt failed for other reasons, try parts next
                    try:
                        init_db(**db_secrets)
                        return
                    except Exception:
                        pass
            else:
                # No URL; try passing parts directly
                try:
                    init_db(**db_secrets)
                    return
                except TypeError:
                    pass
                except Exception:
                    pass

        # 2) Fallback → local SQLite file in project folder
        try:
            init_db(db_path="food.sqlite3")  # preferred explicit argument
            return
        except TypeError:
            pass
        except Exception:
            pass

        # 3) Last resort → legacy no-arg init
        init_db()

    _init_backend()

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
    def _resize_image_to_max_200(file) -> Tuple[bytes, str, str]:
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
        mime = getattr(file, "type", None) or ("image/png" if fmt.upper() == "PNG" else f"image/{fmt.lower()}")
        name = getattr(file, "name", None) or f"image.{fmt.lower()}"
        return img_bytes, mime, name

    def _pil_preview_200(file) -> Image.Image:
        """Return a PIL image preview resized to max 200x200 (no upscaling)."""
        im = Image.open(file).copy()
        im.thumbnail((200, 200))
        return im

    def _make_no_preview_placeholder(size: int = 200) -> Image.Image:
        """
        Create a gray 200x200 image with large dark-gray 'No preview' text,
        leaving a ~10px gap to the edges. Text is auto-sized to fit.
        """
        W, H = size, size
        bg = (220, 220, 220)       # light gray background
        fg = (80, 80, 80)          # dark gray text
        margin = 10
        text = "No\npreview"

        img = Image.new("RGB", (W, H), color=bg)
        draw = ImageDraw.Draw(img)

        def get_font(sz: int):
            for fam in ("DejaVuSans.ttf", "arial.ttf"):
                try:
                    return ImageFont.truetype(fam, sz)
                except Exception:
                    continue
            return ImageFont.load_default()

        max_w, max_h = W - 2 * margin, H - 2 * margin
        font_size = 120
        font = get_font(font_size)

        def measure(f):
            if hasattr(draw, "multiline_textbbox") and isinstance(f, ImageFont.FreeTypeFont):
                b = draw.multiline_textbbox((0, 0), text, font=f, spacing=6, align="center")
                return b[2] - b[0], b[3] - b[1]
            else:
                return draw.multiline_textsize(text, font=f, spacing=6)

        w, h = measure(font)
        while (w > max_w or h > max_h) and font_size > 8:
            font_size -= 2
            font = get_font(font_size)
            w, h = measure(font)

        x = (W - w) / 2
        y = (H - h) / 2
        draw.multiline_text((x, y), text, font=font, fill=fg, align="center", spacing=6)
        return img

    # ---------- ingredients helpers ----------
    def _rows_from_text(ingredients_text: str) -> List[Dict[str, str]]:
        """
        Parse ingredients from stored text.
        Format: 'name<TAB>amount<TAB>unit' per line. Backward compatible with free text.
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
        """Build TSV-like text from ingredient rows; ignore rows without a name."""
        out_lines = []
        for r in rows:
            name = (r.get("name") or "").strip()
            amount = (r.get("amount") or "").strip()
            unit = (r.get("unit") or "").strip()
            if name:
                out_lines.append(f"{name}\t{amount}\t{unit}")
        return "\n".join(out_lines)

    def _render_ingredients_preview(ingredients_text: str):
        """Render ingredients as bullet list in preview; fall back to raw text."""
        rows = _rows_from_text(ingredients_text)
        if rows:
            st.markdown("**Ingredients**")
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
            st.markdown("\n".join(bullets))
        else:
            txt = (ingredients_text or "").strip()
            if txt:
                st.markdown("**Ingredients**")
                safe = html.escape(txt).replace("\n", "<br>")
                st.markdown(f"<div>{safe}</div>", unsafe_allow_html=True)

    def _ingredients_table_editor(state_key_prefix: str) -> List[Dict[str, str]]:
        """Render a table-like editor for ingredients using Streamlit inputs."""
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
            st.markdown(" ")  # spacer

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

        if delete_index is not None:
            if 0 <= delete_index < len(updated_rows):
                updated_rows.pop(delete_index)
                if not updated_rows:
                    updated_rows = [{"name": "", "amount": "", "unit": ""}]
            st.session_state[f"{state_key_prefix}_rows"] = updated_rows
            st.rerun()

        if st.button("➕ Add row", key=f"{state_key_prefix}_addrow"):
            updated_rows.append({"name": "", "amount": "", "unit": ""})
            st.session_state[f"{state_key_prefix}_rows"] = updated_rows
            st.rerun()

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
        st.session_state.pop("add_ing_rows", None)

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
        st.session_state.pop("edit_ing_rows", None)

    # ---------- header ----------
    st.header("Cook Book", divider="gray")
    total = count_recipes()
    st.caption(f"You have **{total}** recipe{'s' if total != 1 else ''} in your cook book.")

    # ========== ADD PAGE ==========
    if ss.cb_mode == "add":
        st.subheader("Add a new recipe")

        if "add_ing_rows" not in st.session_state:
            st.session_state["add_ing_rows"] = [{"name": "", "amount": "", "unit": ""}]

        # Title
        title = st.text_input("Title *", placeholder="e.g., Chicken Wings")

        # Image upload + preview (intrinsic size, up to 200x200)
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

        # Serves (mandatory)
        serves = st.selectbox(
            "For how many people is this recipe served? *",
            options=list(range(1, 21)),
            index=1,  # default to 2
            help="This is used later to scale a shopping list."
        )

        # Ingredients table editor
        add_rows = _ingredients_table_editor("add_ing")

        # Instructions (auto-resize)
        instructions = st.text_area("Instructions", placeholder="Steps…", key="add_instructions")
        components.html(
            """
            <script>
              const doc = window.parent.document;
              function autosize() {
                const el = doc.querySelector('textarea[aria-label="Instructions"]');
                if (!el) return;
                el.style.height = 'auto';
                el.style.height = Math.min(el.scrollHeight + 2, 1000) + 'px';
              }
              const el = doc.querySelector('textarea[aria-label="Instructions"]');
              if (el) {
                el.addEventListener('input', autosize);
                setTimeout(autosize, 50);
              }
            </script>
            """,
            height=0,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Save", use_container_width=True, key="add_save_btn"):
                if not title.strip():
                    st.error("Title is required.")
                else:
                    try:
                        img_bytes = img_mime = img_name = None
                        if uploaded_img is not None:
                            img_bytes, img_mime, img_name = _resize_image_to_max_200(uploaded_img)

                        ingredients_text = _text_from_rows(add_rows)

                        # Try with 'serves', fall back to 'servings' for backward compatibility
                        new_id = None
                        try:
                            new_id = add_recipe(
                                title=title.strip(),
                                ingredients=ingredients_text,
                                instructions=instructions.strip(),
                                image_bytes=img_bytes,
                                image_mime=img_mime,
                                image_filename=img_name,
                                serves=int(serves),
                            )
                        except TypeError:
                            new_id = add_recipe(
                                title=title.strip(),
                                ingredients=ingredients_text,
                                instructions=instructions.strip(),
                                image_bytes=img_bytes,
                                image_mime=img_mime,
                                image_filename=img_name,
                                servings=int(serves),
                            )

                        st.toast(f"Recipe “{title.strip()}” added.", icon="✅")

                        if isinstance(new_id, int):
                            ss.cb_selected_id = new_id
                            ss.cb_mode = "view"
                        else:
                            ss.cb_mode = "list"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add recipe: {e}")
        with c2:
            if st.button("Cancel", use_container_width=True, key="add_cancel_btn"):
                _back_to_list()
                st.rerun()

        return  # Add page shows nothing else

    # ========== VIEW PAGE (preview) ==========
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
        serves_val = 0
        if isinstance(recipe, dict):
            # supports serves / servings / people / persons keys for compatibility
            serves_val = int(
                recipe.get("serves")
                or recipe.get("servings")
                or recipe.get("people")
                or recipe.get("persons")
                or 0
            )

        # Title (big, bold)
        safe_title = html.escape(rtitle)
        st.markdown(
            f"""
            <div style="font-weight: 800; font-size: 1.8rem; line-height: 1.2; margin-bottom: 1rem;">
              {safe_title}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Image or placeholder
        if rimg:
            st.image(rimg, caption=None)  # intrinsic size (<=200x200)
        else:
            placeholder = _make_no_preview_placeholder(200)
            st.image(placeholder, caption=None)

        # Serves sentence
        if serves_val and serves_val > 0:
            plural = "people" if serves_val != 1 else "person"
            # Use markdown to render in regular (black) text instead of caption gray
            st.markdown(f"**Serves for {serves_val} {plural}.**")

        # Ingredients & Instructions
        _render_ingredients_preview(ringing)
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

    # ========== EDIT PAGE ==========
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
        serves_existing = 0
        if isinstance(recipe, dict):
            serves_existing = int(
                recipe.get("serves")
                or recipe.get("servings")
                or recipe.get("people")
                or recipe.get("persons")
                or 0
            )

        st.subheader(f"Edit: {rtitle or 'Untitled'}")

        if "edit_ing_rows" not in st.session_state:
            st.session_state["edit_ing_rows"] = _rows_from_text(orig_ing_text) or [{"name": "", "amount": "", "unit": ""}]

        new_title = st.text_input("Title *", value=rtitle or "")

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

        # Serves (mandatory)
        new_serves = st.selectbox(
            "For how many people is this recipe served? *",
            options=list(range(1, 21)),
            index=max(0, min(19, (serves_existing or 2) - 1)),
            help="This is used later to scale a shopping list."
        )

        # Ingredients editor
        edit_rows = _ingredients_table_editor("edit_ing")

        # Instructions (auto-resize)
        new_instr = st.text_area("Instructions", value=rinstr, key="edit_instructions")
        components.html(
            """
            <script>
              const doc = window.parent.document;
              function autosize() {
                const el = doc.querySelector('textarea[aria-label="Instructions"]');
                if (!el) return;
                el.style.height = 'auto';
                el.style.height = Math.min(el.scrollHeight + 2, 1000) + 'px';
              }
              const el = doc.querySelector('textarea[aria-label="Instructions"]');
              if (el) {
                el.addEventListener('input', autosize);
                setTimeout(autosize, 50);
              }
            </script>
            """,
            height=0,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Save changes", use_container_width=True, key="edit_save_btn"):
                if not new_title.strip():
                    st.error("Title is required.")
                else:
                    try:
                        replace = e_uploaded is not None
                        img_bytes = img_mime = img_name = None
                        if replace:
                            img_bytes, img_mime, img_name = _resize_image_to_max_200(e_uploaded)

                        ingredients_text = _text_from_rows(edit_rows)

                        # Try with 'serves', fall back to 'servings'
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
                                serves=int(new_serves),
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
                                servings=int(new_serves),
                            )

                        st.toast("Recipe updated.", icon="✏️")
                        ss.cb_mode = "view"
                        st.session_state.pop("edit_ing_rows", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update: {e}")
        with c2:
            if st.button("Cancel", use_container_width=True, key="edit_cancel_btn"):
                ss.cb_mode = "view"
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
                  const el = doc.getElementById('sec-{first_letter}');
                  if (el) {{
                    el.scrollIntoView({{behavior: 'instant', block: 'start'}});
                  }}
                </script>
                """,
                height=0,
            )
