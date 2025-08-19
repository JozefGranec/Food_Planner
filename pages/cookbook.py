# pages/cookbook.py  (or pages/1_Cook_Book.py)

import streamlit as st

# --- Robust imports: first try package layout, then fallback to root-level db.py
try:
    from food.db import init_db, add_recipe, list_recipes, get_recipe
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from food.db import init_db, add_recipe, list_recipes, get_recipe

# Ensure DB exists / is migrated each time the page loads
init_db()

st.title("🍳 Cook Book")

# ---------- New Recipe Form ----------
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
        prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=0)
    with col2:
        cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=0)
    with col3:
        servings = st.number_input("Servings", min_value=1, step=1, value=1)

    tags = st.text_input("Tags (comma separated, optional)", placeholder="e.g., chicken, quick")

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
                (st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun())
            except Exception as e:
                st.error(f"Could not save recipe: {e}")

st.divider()

# ---------- List / Search ----------
st.subheader("Your recipes")
search = st.text_input("Search (title or tags)", key="recipe_search")
rows = list_recipes(limit=200, search=(search.strip() or None))

if not rows:
    st.info("No recipes found yet. Add your first one above.")
else:
    for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows:
        total_time = (rprep or 0) + (rcook or 0)
        header = f"{rtitle}  •
