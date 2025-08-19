# streamlit_app.py
import streamlit as st
from services.db import create_db_and_tables
from pages import cookbook, food_plan, shopping_list

st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="wide")
st.title("🍽️ Food Planner")

# Bootstrap DB (idempotent and fast)
create_db_and_tables()

tab1, tab2, tab3 = st.tabs(["Cook Book", "Food Plan", "Shopping List"])

with tab1:
    cookbook.render()

with tab2:
    food_plan.render()

with tab3:
    shopping_list.render()
