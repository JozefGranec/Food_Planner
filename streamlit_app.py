# streamlit_app.py
import streamlit as st
from pages import cookbook, food_plan, shopping_list  # make sure these modules have a render() function

st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="wide")
st.title("🍽️ Food Planner")

# --- Main tabs ---
tab1, tab2, tab3 = st.tabs(["Cook Book", "Food Plan", "Shopping List"])

with tab1:
    cookbook.render()      # <-- Call the render() function from cookbook.py
with tab2:
    food_plan.render()    # <-- Ensure food_plan.py has a render() function
with tab3:
    shopping_list.render() # <-- Ensure shopping_list.py has a render() function
