# pages/cookbook.py  (or pages/1_Cook_Book.py)

import streamlit as st
from food.db import init_db, add_recipe, list_recipes, get_recipe, update_recipe

# Ensure DB exists / migrated
init_db()

st.title("🍳 Cook Book")

# --- session state for edit mode ---
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

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
        prep_minutes = st.number_input("Prep (min)", min_value=0, step=5, value=0, key="new_prep")
    with col2:
        cook_minutes = st.number_input("Cook (min)", min_value=0, step=5, value=0, key="new_cook")
    with col3:
        servings = st.number_input("Servings", min_value=1, step=1, value=1, key="new_servings")

    tags = st.text_input("Tags (comma separated, optional)", placeholder="e.g., chicken, quick", key="new_tags")

    submitted = st.form_submit_button("Save Recipe")

    if submitted:
        if not title.strip():
            st.error("Please provide a title.")
        else:
            try:
                new_id = add_recipe(
                    title=title.strip(),
                    description=(description or "").strip(),
                    ingredients=(ingredients or "").strip(),
                    steps=(steps or "").strip(),
                    tags=(tags or "").strip(),
                    prep_minutes=int(prep_minutes or 0),
                    cook_minutes=int(cook_minutes or 0),
                    servings=int(servings or 1),
                )
                st.success(f"Recipe saved ✅ (ID: {new_id})")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save recipe: {e}")

st.divider()

# ---------- Edit Panel (appears when user clicks Edit) ----------
if st.session_state.edit_id is not None:
    rid = st.session_state.edit_id
    rec = get_recipe(rid)
    if not rec:
        st.warning("Recipe not found.")
        st.session_state.edit_id = None
    else:
        st.subheader(f"✏️ Edit recipe: {rec['title']} (ID {rid})")

        with st.form("edit_recipe_form"):
            etitle = st.text_input("Title *", value=rec["title"])
            edescription = st.text_area("Short Description", value=rec["description"] or "")
            eingredients = st.text_area("Ingredients (one per line, optional)", value=rec["ingredients"] or "")
            esteps = st.text_area("Steps (one per line, optional)", value=rec["steps"] or "")

            col1, col2, col3 = st.columns(3)
            with col1:
                e_prep = st.number_input("Prep (min)", min_value=0, step=5, value=int(rec["prep_minutes"] or 0))
            with col2:
                e_cook = st.number_input("Cook (min)", min_value=0, step=5, value=int(rec["cook_minutes"] or 0))
            with col3:
                e_serv = st.number_input("Servings", min_value=1, step=1, value=int(rec["servings"] or 1))

            e_tags = st.text_input("Tags (comma separated, optional)", value=rec["tags"] or "")

            c1, c2 = st.columns(2)
            save_edit = c1.form_submit_button("Save changes ✅")
            cancel_edit = c2.form_submit_button("Cancel")

            if save_edit:
                if not etitle.strip():
                    st.error("Please provide a title.")
                else:
                    try:
                        changed = update_recipe(
                            recipe_id=rid,
                            title=etitle.strip(),
                            description=(edescription or "").strip(),
                            ingredients=(eingredients or "").strip(),
                            steps=(esteps or "").strip(),
                            tags=(e_tags or "").strip(),
                            prep_minutes=int(e_prep or 0),
                            cook_minutes=int(e_cook or 0),
                            servings=int(e_serv or 1),
                        )
                        if changed:
                            st.success("Recipe updated ✅")
                        else:
                            st.info("No changes detected.")
                        st.session_state.edit_id = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update recipe: {e}")

            if cancel_edit:
                st.session_state.edit_id = None
                st.rerun()

st.subheader("Your recipes")
search = st.text_input("Search (title or tags)", key="recipe_search")
rows = list_recipes(limit=200, search=(search.strip() or None))

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

            if (r.get("description") or "").strip():
                st.markdown("**Notes**")
                st.write(r["description"])

            if (r.get("ingredients") or "").strip():
                st.markdown("**Ingredients**")
                st.markdown("\n".join(
                    f"- {line}" for line in r["ingredients"].splitlines() if line.strip()
                ))

            if (r.get("steps") or "").strip():
                st.markdown("**Steps**")
                st.markdown("\n".join(
                    f"{i+1}. {line}"
                    for i, line in enumerate([ln for ln in r["steps"].splitlines() if ln.strip()])
                ))

            # Edit button for this recipe
            if st.button("✏️ Edit this recipe", key=f"edit_btn_{rid}"):
                st.session_state.edit_id = rid
                st.rerun()
