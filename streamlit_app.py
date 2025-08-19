# streamlit_app.py
import streamlit as st
from food.db import init_db

# Import page modules (make sure each has a render() function)
from pages import cookbook, food_plan, shopping_list

# Set page config
st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="wide")
st.title("🍽️ Food Planner")

# Initialize database (creates tables on first run)
init_db()  # this replaces create_db_and_tables

# Create tabs for pages
tab1, tab2, tab3 = st.tabs(["Cook Book", "Food Plan", "Shopping List"])

with tab1:
    cookbook.render()        # cookbook.py must have a render() function

with tab2:
    food_plan.render()       # food_plan.py must have a render() function

with tab3:
    shopping_list.render()   # shopping_list.py must have a render() function
