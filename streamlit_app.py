# streamlit_app.py
import streamlit as st
from pathlib import Path
from pages import household, cookbook, food_plan, shopping_list  # each must expose render()

# --- Paths ---
APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "pictures" / "Shop_n_Home.jpeg"  # <-- JPEG logo

# --- Page config ---
st.set_page_config(
    page_title="Food Planner",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🍽️",
    layout="wide"
)

# --- Custom CSS for sticky white banner ---
st.markdown(
    """
    <style>
        .sticky-banner {
            position: sticky;
            top: 0;
            z-index: 9999;
            background-color: white;   /* white background */
            padding: 15px 0;
            border-bottom: 1px solid #e5e7eb;
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Header ---
if LOGO_PATH.exists():
    st.markdown('<div class="sticky-banner">', unsafe_allow_html=True)
    st.image(str(LOGO_PATH), use_container_width=False, width=300)  # centered automatically
    st.markdown('</div>', unsafe_allow_html=True)
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
