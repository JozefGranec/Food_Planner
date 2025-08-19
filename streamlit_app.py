import streamlit as st
import pandas as pd
import json
import base64
import uuid

st.set_page_config(page_title="Food Planner • The Cook Book", page_icon="🍳", layout="wide")
st.title("🍳 The Cook Book")
st.caption("Store your recipes with picture, instructions, and structured ingredients.")

# ---------- helpers ----------
def _init_state():
    if "cookbook" not in st.session_state:
        st.session_state.cookbook = []  # list[dict]
    if "page" not in st.session_state:
        st.session_state.page = "List"  # or "Add" or "View"
    if "active_recipe_id" not in st.session_state:
        st.session_state.active_recipe_id = None

def _img_to_b64(file):
    if not file:
        return None
    data = file.read()
    return base64.b64encode(data).decode("utf-8")

def _b64_to_html_img(b64: str, width: int = 300):
    if not b64:
        return None
    return f'<img src="data:image/*;base64,{b64}" width="{width}" />'

def _find_recipe(rid: str):
    for r in st.session_state.cookbook:
        if r["id"] == rid:
            return r
    return None

def _export_json() -> str:
    return json.dumps(st.session_state.cookbook, ensure_ascii=False, indent=2)

def _import_json(text: str):
    try:
        data = json.loads(text)
        if isinstance(data, list):
            # basic schema sanity
            for r in data:
                assert isinstance(r.get("id",""), str)
                assert isinstance(r.get("name",""), str)
                assert isinstance(r.get("instructions",""), str)
                assert isinstance(r.get("ingredients",[]), list)
            st.session_state.cookbook = data
            st.success("Cookbook imported.")
        else:
            st.error("Invalid JSON format. Expected a list of recipes.")
    except Exception as e:
        st.error(f"Import failed: {e}")

# ---------- UI: sidebar ----------
_init_state()
with st.sidebar:
    st.header("Cook Book")
    choice = st.radio(
        "Navigation",
        ["List recipes", "Add new recipe", "Import / Export"],
        index=["List recipes", "Add new recipe", "Import / Export"].index(
            "Add new recipe" if st.session_state.page == "Add" else
            "List recipes" if st.session_state.page == "List" else
            "Import / Export"
        ),
    )
    if choice == "List recipes":
        st.session_state.page = "List"
    elif choice == "Add new recipe":
        st.session_state.page = "Add"
    else:
        st.session_state.page = "ImportExport"

# ---------- PAGES ----------
UNITS = ["g", "kg", "ml", "l", "pcs", "tbsp", "tsp", "cup", "pinch"]

def page_list():
    st.subheader("📚 Your Recipes")

    if not st.session_state.cookbook:
        st.info("No recipes yet. Go to **Add new recipe** to create your first one.")
        return

    # simple searchable table
    q = st.text_input("Search by name or ingredient...")
    filtered = []
    for r in st.session_state.cookbook:
        hay = (r["name"] + " " + " ".join(i["name"] for i in r["ingredients"])).lower()
        if (q or "").lower() in hay:
            filtered.append(r)

    # cards
    grid = st.columns(3)
    for i, r in enumerate(filtered):
        with grid[i % 3]:
            st.markdown(f"### {r['name']}")
            if r.get("image_b64"):
                st.image(base64.b64decode(r["image_b64"]), use_container_width=True)
            st.caption(f"{len(r['ingredients'])} ingredients")
            if st.button("View", key=f"view_{r['id']}"):
                st.session_state.active_recipe_id = r["id"]
                st.session_state.page = "View"
                st.experimental_rerun()
            with st.popover("Quick delete", use_container_width=True):
                st.warning("This will permanently remove the recipe.")
                if st.button("Confirm delete", key=f"del_{r['id']}"):
                    st.session_state.cookbook = [x for x in st.session_state.cookbook if x["id"] != r["id"]]
                    st.success("Deleted.")
                    st.experimental_rerun()

def page_add():
    st.subheader("➕ Add New Recipe")

    with st.form("add_recipe", clear_on_submit=True):
        name = st.text_input("Recipe name*", placeholder="e.g., Pancakes")
        img_file = st.file_uploader("Food picture (optional)", type=["png","jpg","jpeg","webp"])
        instructions = st.text_area("Preparation instructions*", height=180, placeholder="Step-by-step instructions...")

        st.markdown("**Ingredients**")
        st.caption("Tip: Use the table to add rows; fill name, amount, and choose units.")
        # Start with 5 empty rows for convenience
        df_init = pd.DataFrame([
            {"name": "", "amount": 0.0, "unit": "g"} for _ in range(5)
        ])
        edited = st.data_editor(
            df_init,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "name": st.column_config.TextColumn("Ingredient name", required=False),
                "amount": st.column_config.NumberColumn("Amount", step=0.1, required=False, format="%.3f"),
                "unit": st.column_config.SelectboxColumn("Unit", options=UNITS, required=False),
            },
        )

        submitted = st.form_submit_button("Save recipe", type="primary")
        if submitted:
            # validate
            if not name.strip():
                st.error("Please provide a recipe name.")
                return
            if not instructions.strip():
                st.error("Please provide preparation instructions.")
                return

            ingredients = []
            for _, row in edited.iterrows():
                n = (row.get("name") or "").strip()
                amt = row.get("amount")
                unit = (row.get("unit") or "").strip() or "pcs"
                if n:  # only keep filled rows
                    try:
                        amt_f = float(amt) if amt is not None else 0.0
                    except Exception:
                        amt_f = 0.0
                    ingredients.append({"name": n, "amount": amt_f, "unit": unit})

            recipe = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "instructions": instructions.strip(),
                "ingredients": ingredients,
                "image_b64": _img_to_b64(img_file),
            }
            st.session_state.cookbook.append(recipe)
            st.success(f"Added **{recipe['name']}**.")
            st.session_state.active_recipe_id = recipe["id"]
            st.session_state.page = "View"
            st.experimental_rerun()

def page_view():
    rid = st.session_state.active_recipe_id
    recipe = _find_recipe(rid)
    if not recipe:
        st.warning("Recipe not found.")
        st.session_state.page = "List"
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
        if recipe["ingredients"]:
            df = pd.DataFrame(recipe["ingredients"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No ingredients listed.")
        st.divider()
        if st.button("Back to list"):
            st.session_state.page = "List"
            st.experimental_rerun()

    # Simple inline edit (optional)
    with st.expander("✏️ Edit this recipe"):
        with st.form(f"edit_{rid}"):
            name = st.text_input("Recipe name*", value=recipe["name"])
            img_file = st.file_uploader("Replace picture (optional)", type=["png","jpg","jpeg","webp"])
            instructions = st.text_area("Preparation instructions*", height=180, value=recipe["instructions"])
            df_edit = pd.DataFrame(recipe["ingredients"])
            edited = st.data_editor(
                df_edit,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "name": st.column_config.TextColumn("Ingredient name"),
                    "amount": st.column_config.NumberColumn("Amount", step=0.1, format="%.3f"),
                    "unit": st.column_config.SelectboxColumn("Unit", options=UNITS),
                },
            )
            save = st.form_submit_button("Save changes", type="primary")
            if save:
                recipe["name"] = name.strip()
                recipe["instructions"] = instructions.strip()
                # update ingredients
                new_ings = []
                for _, row in edited.iterrows():
                    n = (row.get("name") or "").strip()
                    if n:
                        try:
                            amt = float(row.get("amount")) if row.get("amount") is not None else 0.0
                        except Exception:
                            amt = 0.0
                        unit = (row.get("unit") or "").strip() or "pcs"
                        new_ings.append({"name": n, "amount": amt, "unit": unit})
                recipe["ingredients"] = new_ings
                # update image if provided
                if img_file:
                    recipe["image_b64"] = _img_to_b64(img_file)
                st.success("Recipe updated.")
                st.experimental_rerun()

def page_import_export():
    st.subheader("📦 Import / Export")
    st.write("Use this to back up or move your cookbook between sessions.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Export**")
        data = _export_json()
        st.download_button(
            "Download cookbook.json",
            data=data,
            file_name="cookbook.json",
            mime="application/json",
        )
    with col2:
        st.markdown("**Import**")
        up = st.file_uploader("Upload cookbook.json", type=["json"])
        if up and st.button("Import now"):
            _import_json(up.read().decode("utf-8"))

# route
if st.session_state.page == "List":
    page_list()
elif st.session_state.page == "Add":
    page_add()
elif st.session_state.page == "View":
    page_view()
else:
    page_import_export()
