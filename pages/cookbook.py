# pages/cookbook.py
import base64
import pandas as pd
import streamlit as st
from repository.recipes_repo import (
    list_recipes_cached, get_recipe, create_recipe, update_recipe, delete_recipe
)

UNITS = ["g", "kg", "ml", "l", "pcs", "tbsp", "tsp", "cup", "pinch"]

def _img_to_b64(file):
    if not file:
        return None
    return base64.b64encode(file.read()).decode("utf-8")

def render():
    st.header("🍳 Cook Book")
    tab_list, tab_add = st.tabs(["Recipes", "Add new"])

    # ----- LIST -----
    with tab_list:
        top1, top2 = st.columns([2, 1])
        q = top1.text_input("Search by name…", placeholder="e.g., Pancakes")
        if top2.button("Refresh"):
            list_recipes_cached.clear()

        recipes = list_recipes_cached(q)
        if q:
            ql = q.lower()
            recipes = [
                r for r in recipes
                if (ql in r.name.lower()) or any(ql in i.name.lower() for i in r.ingredients or [])
            ]

        if not recipes:
            st.info("No recipes yet. Add your first one in the **Add new** tab.")
        else:
            cols = st.columns(3)
            for i, r in enumerate(recipes):
                with cols[i % 3]:
                    st.markdown(f"### {r.name}")
                    if r.image_b64:
                        st.image(base64.b64decode(r.image_b64), use_container_width=True)
                    st.caption(f"{len(r.ingredients or [])} ingredients")
                    c1, c2 = st.columns(2)
                    if c1.button("View / Edit", key=f"v{r.id}"):
                        _view_edit_dialog(r.id)
                    if c2.button("Delete", key=f"d{r.id}"):
                        delete_recipe(r.id)
                        st.success("Deleted.")
                        st.experimental_rerun()

    # ----- ADD -----
    with tab_add:
        st.subheader("Add New Recipe")
        with st.form("add_recipe", clear_on_submit=True):
            name = st.text_input("Recipe name*", placeholder="e.g., Pancakes")
            img_file = st.file_uploader("Food picture (optional)", type=["png","jpg","jpeg","webp"])
            instructions = st.text_area("Preparation instructions*", height=180)

            st.markdown("**Ingredients**")
            df_init = pd.DataFrame([{"name": "", "amount": 0.0, "unit": "g"} for _ in range(5)])
            grid = st.data_editor(
                df_init, num_rows="dynamic", use_container_width=True, hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Ingredient"),
                    "amount": st.column_config.NumberColumn("Amount", step=0.1, format="%.3f"),
                    "unit": st.column_config.SelectboxColumn("Unit", options=UNITS),
                }
            )

            c1, c2 = st.columns(2)
            save = c1.form_submit_button("Save recipe", type="primary")
            cancel = c2.form_submit_button("Cancel")

            if save:
                if not name.strip():
                    st.error("Please provide a recipe name."); st.stop()
                if not instructions.strip():
                    st.error("Please provide instructions."); st.stop()

                ings = []
                for _, row in grid.iterrows():
                    n = (row.get("name") or "").strip()
                    if not n: continue
                    amt = float(row.get("amount") or 0.0)
                    unit = (row.get("unit") or "pcs").strip()
                    ings.append({"name": n, "amount": amt, "unit": unit})
                rid = create_recipe(name, instructions, ings, _img_to_b64(img_file))
                st.success(f"Added **{name}**.")
                _view_edit_dialog(rid)  # open editor

def _view_edit_dialog(recipe_id: int):
    r = get_recipe(recipe_id)
    if not r:
        st.error("Recipe not found."); return

    with st.expander(f"✏️ Edit: {r.name}", expanded=True):
        with st.form(f"edit_{recipe_id}"):
            name = st.text_input("Recipe name*", value=r.name)
            img_file = st.file_uploader("Replace picture (optional)", type=["png","jpg","jpeg","webp"])
            instructions = st.text_area("Preparation instructions*", value=r.instructions, height=180)

            df = pd.DataFrame(
                [{"name": i.name, "amount": i.amount, "unit": i.unit} for i in (r.ingredients or [])]
            )
            if df.empty:
                df = pd.DataFrame([{"name": "", "amount": 0.0, "unit": "g"}])

            edited = st.data_editor(
                df, num_rows="dynamic", use_container_width=True, hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Ingredient"),
                    "amount": st.column_config.NumberColumn("Amount", step=0.1, format="%.3f"),
                    "unit": st.column_config.SelectboxColumn("Unit", options=UNITS),
                }
            )

            c1, c2 = st.columns(2)
            save = c1.form_submit_button("Save changes", type="primary")
            close = c2.form_submit_button("Close")

            if save:
                ings = []
                for _, row in edited.iterrows():
                    n = (row.get("name") or "").strip()
                    if not n: continue
                    amt = float(row.get("amount") or 0.0)
                    unit = (row.get("unit") or "pcs").strip()
                    ings.append({"name": n, "amount": amt, "unit": unit})
                img_b64 = _img_to_b64(img_file) if img_file else None
                ok = update_recipe(recipe_id, name, instructions, ings, img_b64)
                if ok:
                    st.success("Saved.")
                    list_recipes_cached.clear()
                else:
                    st.error("Failed to save.")
