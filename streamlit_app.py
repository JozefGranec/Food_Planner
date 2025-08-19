import streamlit as st
import pandas as pd
from io import StringIO

st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="centered")

st.title("🍽️ Weekly Food Planner")
st.caption("Plan meals for the week and auto-generate a shopping list.")

# --- Data model (simple example you can replace with your own) ---
# Define a small library of meals -> ingredients
MEALS = {
    "Spaghetti Bolognese": ["spaghetti 500g", "minced beef 400g", "tomato passata 500ml", "onion", "garlic", "olive oil", "salt", "pepper"],
    "Chicken Salad": ["chicken breast 400g", "lettuce", "tomatoes", "cucumber", "olive oil", "lemon", "salt", "pepper"],
    "Veggie Stir Fry": ["mixed vegetables 500g", "soy sauce", "rice 400g", "garlic", "ginger"],
    "Omelette": ["eggs 6", "cheese 100g", "spinach 100g", "salt", "pepper"],
    "Pancakes": ["flour 200g", "milk 300ml", "eggs 2", "sugar", "butter"],
}

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

st.sidebar.header("Meals Library")
with st.sidebar:
    st.write("These are the example meals included:")
    for m, ings in MEALS.items():
        st.write(f"- **{m}**: {', '.join(ings)}")
    st.info("Tip: Replace MEALS with your own data or load from a CSV later.")

st.subheader("Plan your week")
st.write("Select a meal for each day (or leave blank).")
if "plan" not in st.session_state:
    st.session_state.plan = {d: "" for d in DAYS}

cols = st.columns(2)
for i, day in enumerate(DAYS):
    with cols[i % 2]:
        st.session_state.plan[day] = st.selectbox(
            day, [""] + list(MEALS.keys()), index=0, key=f"sb_{day}"
        )

# Show plan
plan_df = pd.DataFrame({"Day": DAYS, "Meal": [st.session_state.plan[d] for d in DAYS]})
st.subheader("📅 Your Weekly Plan")
st.dataframe(plan_df, use_container_width=True)

# Build shopping list
def build_shopping_list(plan: dict) -> list[str]:
    items: list[str] = []
    for meal in plan.values():
        if meal and meal in MEALS:
            items.extend(MEALS[meal])
    # normalize & deduplicate (basic)
    items = [x.strip() for x in items if x and x.strip()]
    # A simple unique sort; you can implement quantity merging later
    return sorted(set(items), key=lambda s: s.lower())

shopping_list = build_shopping_list(st.session_state.plan)

st.subheader("🛒 Shopping List")
if shopping_list:
    for it in shopping_list:
        st.write(f"- {it}")
else:
    st.write("No items yet. Choose meals to generate a list.")

# Download buttons
if shopping_list:
    txt = "\n".join(shopping_list)
    csv = "item\n" + "\n".join(shopping_list)

    st.download_button(
        "Download as TXT",
        data=txt,
        file_name="shopping_list.txt",
        mime="text/plain",
    )
    st.download_button(
        "Download as CSV",
        data=csv.encode("utf-8"),
        file_name="shopping_list.csv",
        mime="text/csv",
    )

st.caption("v0.1 • Streamlit demo. Extend with your own meal database, nutrition, budgets, etc.")
