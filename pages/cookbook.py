# pages/cookbook.py  (or pages/1_Cook_Book.py)

import streamlit as st

# --- Robust imports: works with either `food/db.py` or root-level `db.py`
try:
    # Preferred clean structure: project_root/food/db.py (with food/__init__.py)
    from food.db import init_db, add_recipe, list_recipes, get_recipe
except ModuleNotFoundError:
    # Fallback: project_root/db.py, add project root to sys.path
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from db import init_db, add_recipe, list_recipes, get_recipe

# Ensure DB schema exists every time this page runs
init_db()

st.title("🍳 Cook Book")

# ---------- New Recipe Form ----------
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
                    description=(description or "").strip(),
                    ingredients=ingredients.strip(),
                    steps=steps.strip(),
                    tags=(tags or "").strip(),
                    prep_minutes=int(prep_minutes),
                    cook_minutes=int(cook_minutes),
                    servings=int(servings),
                )
                st.success(f"Recipe saved ✅ (ID: {new_id})")
                st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
            except Exception as e:
                st.error(f"Could not save recipe: {e}")

st.divider()

# ---------- List / Search ----------
st.subheader("Your recipes")
search = st.text_input("Search (title or tags)", key="recipe_search")
rows = list_recipes(limit=200, search=search.strip() or None)

if not rows:
    st.info("No recipes found yet. Add your first one above.")
else:
    for rid, rtitle, rtags, rserv, rprep, rcook, rcreated in rows:
        total_time = (rprep or 0) + (rcook or 0)
        header = f"{rtitle}  •  {rserv} servings  •  {total_time} min total"
        with st.expander(header):
            st.caption(f"Tags: {rtags or '—'}  |  Added: {rcreated}")

            r = get_recipe(rid)
            if not r:
                st.warning("Could not load this recipe’s details.")
                continue

            # Details
            if r.get("description"):
                st.markdown("**Notes**")
                st.write(r["description"])

            st.markdown("**Ingredients**")
            st.markdown("\n".join(f"- {line}" for line in r["ingredients"].splitlines() if line.strip()))

            st.markdown("**Steps**")
            st.markdown("\n".join(f"{i+1}. {line}" for i, line in enumerate(
                [ln for ln in r["steps"].splitlines() if ln.strip()]
            )))
