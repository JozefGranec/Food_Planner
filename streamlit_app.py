import streamlit as st
import pandas as pd
import json
import base64
import uuid

# ----------------- App setup -----------------
st.set_page_config(page_title="Food Planner • The Cook Book", page_icon="🍳", layout="wide")
st.title("🍳 The Cook Book")
st.caption("Store recipes with picture, instructions, and structured ingredients (name, amount, unit).")

# ----------------- State & helpers -----------------
UNITS = ["g", "kg", "ml", "l", "pcs", "tbsp", "tsp", "cup", "pinch"]

def init_state():
    if "cookbook" not in st.session_state:
        st.session_state.cookbook: list[dict] = []   # [{id,name,instructions,ingredients:[{name,amount,unit}],image_b64}]
    if "page" not in st.session_state:
        st.session_state.page = "List"              # "List" | "Add" | "View"
    if "active_recipe_id" not in st.session_state:
        st.session_state.active_recipe_id = None

def img_to_b64(file):
    if not file:
        return None
    data = file.read()
    return base64.b64encode(data).decode("utf-8")

def find_recipe(rid: str):
    for r in st.session_state.cookbook:
        if r["id"] == rid:
            return r
    return None

def export_json() -> str:
    return json.dumps(st.session_state.cookbook, ensure_ascii=False, indent=2)

def import_json_text(text: str):
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of recipe objects.")
    # light schema check
    for r in data:
        _ = r.get("id"), r.get("name"), r.get("instructions"), r.get("ingredients")
    st.session_state.cookbook = data

init_state()

# ----------------- Pages -----------------
def page_list():
    st.subheader("📚 Your Recipes")

    # Primary entry point: Add button here (no sidebar)
    if st.button("➕ Add new recipe", type="primary"):
        st.session_state.page = "Add"
        st.experimental_rerun()

    # Search
    q = st.text_input("Search by name or ingredient...", placeholder="e.g., Pancakes or flour")

    recipes = st.session_state.cookbook
    if q:
        ql = q.lower()
        recipes = [
            r for r in recipes
            if (ql in r["name"].lower()) or any(ql in i["name"].lower() for i in r.get("ingredients", []))
        ]

    if not recipes:
        st.info("No recipes yet. Click **“➕ Add new recipe”** to create your first one.")
        return

    # Responsive card grid
    cols = st.columns(3)
    for i, r in enumerate(recipes):
        with cols[i % 3]:
            st.markdown(f"### {r['name']}")
            if r.get("image_b64"):
                st.image(base64.b64decode(r["image_b64"]), use_container_width=True)
            st.caption(f"{len(r.get('ingredients', []))} ingredients")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("View", key=f"view_{r['id']}"):
                    st.session_state.active_recipe_id = r["id"]
                    st.session_state.page = "View"
                    st.experimental_rerun()
            with c2:
                with st.popover("Delete", use_container_width=True):
                    st.warning("This will permanently delete the recipe.")
                    if st.button("Confirm delete", key=f"del_{r['id']}"):
                        st.session_state.cookbook = [x for x in st.session_state.cookbook if x["id"] != r["id"]]
                        st.success("Deleted.")
                        st.experimental_rerun()

def page_add():
    st.subheader("➕ Add New Recipe")

    with st.form("add_recipe", clear_on_submit=True):
        name = st.text_input("Recipe name*", placeholder="e.g., Pancakes")
        img_file = st.file_uploader("Food picture (optional)", type=["png", "jpg", "jpeg", "webp"])
        instructions = st.text_area(
            "Preparation instructions*",
            height=180,
            placeholder="Write step-by-step preparation..."
        )

        st.markdown("**Ingredients**")
        st.caption("Add rows as needed. Example: Flour — 0.5 — kg")
        init_rows = pd.DataFrame([{"name": "", "amount": 0.0, "unit": "g"} for _ in range(5)])
        edited = st.data_editor(
            init_rows,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Ingredient name"),
                "amount": st.column_config.NumberColumn("Amount", step=0.1, format="%.3f"),
                "unit": st.column_config.SelectboxColumn("Unit", options=UNITS),
            },
        )

        left, right = st.columns([1, 1])
        submitted = left.form_submit_button("Save recipe", type="primary")
        cancel = right.form_submit_button("Cancel")

        if cancel:
            st.session_state.page = "List"
            st.experimental_rerun()

        if submitted:
            # Validation
            if not name.strip():
                st.error("Please provide a recipe name.")
                st.stop()
            if not instructions.strip():
                st.error("Please provide preparation instructions.")
                st.stop()

            ingredients = []
            for _, row in edited.iterrows():
                ing_name = (row.get("name") or "").strip()
                if not ing_name:
                    continue
                try:
                    amt = float(row.get("amount")) if row.get("amount") is not None else 0.0
                except Exception:
                    amt = 0.0
                unit = (row.get("unit") or "").strip() or "pcs"
                ingredients.append({"name": ing_name, "amount": amt, "unit": unit})

            recipe = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "instructions": instructions.strip(),
                "ingredients": ingredients,
                "image_b64": img_to_b64(img_file),
            }
            st.session_state.cookbook.append(recipe)
            st.success(f"Added **{recipe['name']}**.")
            st.session_state.active_recipe_id = recipe["id"]
            st.session_state.page = "View"
            st.experimental_rerun()

def page_view():
    rid = st.session_state.active_recipe_id
    recipe = find_recipe(rid)
    if not recipe:
        st.warning("Recipe not found.")
        st.session_state.page = "List"
        st.experimental_rerun()
        return

    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"## {recipe['name']}")
        if recipe.get("image_b64"):
            st.image(base64.b64decode(recipe["image_b64"]), use_container_width=True)
        st.markdown("### Instructions")
        st.write(recipe["instructions"])

    with right:
        st.markdown("### Ingredients")
        if recipe.get("ingredients"):
            df = pd.DataFrame(recipe["ingredients"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No ingredients listed.")

        st.divider()
        col_b, col_e = st.columns(2)
        if col_b.button("⬅️ Back to list"):
            st.session_state.page = "List"
            st.experimental_rerun()

    # Inline Edit
    with st.expander("✏️ Edit this recipe"):
        with st.form(f"edit_{rid}"):
            name = st.text_input("Recipe name*", value=recipe["name"])
            img_file = st.file_uploader("Replace picture (optional)", type=["png", "jpg", "jpeg", "webp"])
            instructions = st.text_area("Preparation instructions*", height=180, value=recipe["instructions"])

            df_edit = pd.DataFrame(recipe.get("ingredients", [])) if recipe.get("ingredients") else pd.DataFrame(
                [{"name": "", "amount": 0.0, "unit": "g"}]
            )
            edited = st.data_editor(
                df_edit,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Ingredient name"),
                    "amount": st.column_config.NumberColumn("Amount", step=0.1, format="%.3f"),
                    "unit": st.column_config.SelectboxColumn("Unit", options=UNITS),
                },
            )

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("Save changes", type="primary")
            delete = col2.form_submit_button("Delete recipe", help="Permanently delete this recipe")

            if save:
                recipe["name"] = name.strip()
                recipe["instructions"] = instructions.strip()

                new_ings = []
                for _, row in edited.iterrows():
                    ing_name = (row.get("name") or "").strip()
                    if not ing_name:
                        continue
                    try:
                        amt = float(row.get("amount")) if row.get("amount") is not None else 0.0
                    except Exception:
                        amt = 0.0
                    unit = (row.get("unit") or "").strip() or "pcs"
                    new_ings.append({"name": ing_name, "amount": amt, "unit": unit})
                recipe["ingredients"] = new_ings

                if img_file:
                    recipe["image_b64"] = img_to_b64(img_file)

                st.success("Recipe updated.")
                st.experimental_rerun()

            if delete:
                st.session_state.cookbook = [x for x in st.session_state.cookbook if x["id"] != recipe["id"]]
                st.success("Recipe deleted.")
                st.session_state.page = "List"
                st.experimental_rerun()

def page_import_export():
    st.subheader("📦 Import / Export your cookbook")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Export**")
        data = export_json()
        st.download_button(
            "Download cookbook.json",
            data=data,
            file_name="cookbook.json",
            mime="application/json",
            use_container_width=True,
        )

    with c2:
        st.markdown("**Import**")
        up = st.file_uploader("Upload cookbook.json", type=["json"])
        if up and st.button("Import now", use_container_width=True):
            try:
                import_json_text(up.read().decode("utf-8"))
                st.success("Cookbook imported.")
                st.session_state.page = "List"
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

# ----------------- Top-level navigation (no sidebar) -----------------
tab1, tab2 = st.tabs(["Cook Book", "Import / Export"])

with tab1:
    if st.session_state.page == "List":
        page_list()
    elif st.session_state.page == "Add":
        page_add()
    elif st.session_state.page == "View":
        page_view()
    else:
        st.session_state.page = "List"
        page_list()

with tab2:
    page_import_export()
