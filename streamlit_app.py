# streamlit_app.py
import streamlit as st
from pages import household, cookbook, food_plan, shopping_list  # make sure these modules have a render() function

st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="wide")
st.title("🍽️ Food Planner")

# --- Main tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Household","Cook Book", "Food Plan", "Shopping List"])

with tab1:
    household.render()      # <-- Call the render() function from household.py
with tab2:
    cookbook.render()      # <-- Call the render() function from cookbook.py
with tab3:
    food_plan.render()    # <-- Ensure food_plan.py has a render() function
with tab4:
    shopping_list.render() # <-- Ensure shopping_list.py has a render() function




