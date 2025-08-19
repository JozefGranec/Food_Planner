# put this at the top of pages/cookbook.py

import sys, os
print("CWD:", os.getcwd())
print("sys.path[0]:", sys.path[0])
print("Full sys.path:")
for p in sys.path:
    print("   ", p)

from db import init_db, add_recipe, list_recipes, get_recipe
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))  # add project root to import path

import streamlit as st
from food.db import init_db, add_recipe, list_recipes, get_recipe

# Ensure the DB and table exist every time this page loads
init_db()

st.title("🍳 Cook Book")

with st.form("new_recipe_form", clear_on_submit=True):
    st.subheader("Add a new recipe")
    title = st.text_input("Title *", placeholder="e.g., Lemon Garlic Chicken")
    description = st.text_area("Short Description", placeholder="A bright, zesty weeknight chicken.")
    ingredients = st.text_area(
        "Ingredients * (one per line)",
        placeholder="2 chicken breasts\n1 lemon (zest & juice)\n2 cloves garlic, minced\n1 tbsp olive oil\nSalt & pepper"
    )
    steps = st.text_area(
        "Steps * (one per line)",
        placeholder="Preheat oven to 200°C\nMix marinade\nCoat chicken\nBake 20–25 min"
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=10)
    with col2:
        cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=20)
    with col3:
        servings = st.number_input("Servings", min_value=1, step=1, value=2)

    tags = st.text_input("Tags (comma separated)", placeholder="chicken, quick, weeknight")

    submitted = st.form_submit_button("Save Recipe")

    if submitted:
        # Basic validation
        if not title.strip():
            st.error("Please provide a title.")
        elif not ingredients.strip():
            st.error("Please provide at least one ingredient.")
        elif not steps.strip():
            st.error("Please provide at least one step.")
        else:
            try:
                new_id = add_recipe(
                    title=title.strip(),
                    description=description.strip(),
                    ingredients=ingredients.strip(),
                    steps=steps.strip(),
                    tags=tags.strip(),
                    prep_minutes=int(prep_minutes),
                    cook_minutes=int(cook_minutes),
                    servings=int(servings),
                )
                st.success(f"Recipe saved ✅ (ID: {new_id})")
                st.rerun()  # refresh list below
            except Exception as e:
                # If something goes wrong, show it
                st.error(f"Could not save recipe: {e}")

st.divider()
st.subheader("Your recipes")

search = st.text_input("Search (title or tags)", key="recipe_search")
rows = list_recipes(limit=200, search=search.strip() or None)

if not rows:
    st.info("No recipes found yet. Add your first one above.")
else:
    for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows:
        with st.expander(f"{rtitle}  •  {rserv} servings  •  {rprep+rcook} min total"):
            st.caption(f"Tags: {rtags or '—'}  |  Added: {rcreated}")
            r = get_recipe(rid)
            if r:
                st.markdown("**Ingredients**")
                st.markdown("\n".join(f"- {line}" for line in r["ingredients"].splitlines()))
                st.markdown("**Steps**")
                st.markdown("\n".join(f"{i+1}. {line}" for i, line in enumerate(r["steps"].splitlines())))
                if r["description"]:
                    st.markdown("**Notes**")
                    st.write(r["description"])
