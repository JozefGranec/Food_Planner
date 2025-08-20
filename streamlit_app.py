# streamlit_app.py
import streamlit as st
from pathlib import Path
from pages import household, cookbook, food_plan, shopping_list  # each must expose render()

# --- Paths ---
APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "pictures" / "Shop_n_Home.jpeg"

# --- Page config (use your logo as the page icon if available) ---
st.set_page_config(
    page_title="Food Planner",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🍽️",
    layout="wide"
)

# --- Header: show image instead of title ---
if LOGO_PATH.exists():
    # Center the logo nicely
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(str(LOGO_PATH), caption=None, use_column_width=True)
else:
    st.title("🍽️ Food Planner")

# --- Main tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Household", "Cook Book", "Food Plan", "Shopping List"])

with tab1:
    household.render()
with tab2:
    cookbook.render()
with tab3:
    food_plan.render()
with tab4:
    shopping_list.render()

