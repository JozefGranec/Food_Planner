# streamlit_app.py
import streamlit as st
from pathlib import Path
from pages import household, cookbook, food_plan, shopping_list  # each must expose render()

# --- Paths ---
APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "pictures" / "Shop_n_Home.jpeg"  # <-- updated to .jpeg

# --- Page config ---
st.set_page_config(
    page_title="Food Planner",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🍽️",  # favicon
    layout="wide"
)

# --- Custom CSS for sticky banner ---
st.markdown(
    """
    <style>
        .banner {
            position: sticky;       /* makes it stick while scrolling */
            top: 0;
            z-index: 9999;          /* stays on top */
            background-color: #f8f9fa;
            padding: 14px 0;
            border-bottom: 1px solid #e5e7eb;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            text-align: center;
        }
        .banner img {
            max-width: 300px;       /* adjust as needed */
            width: 100%;
            height: auto;
        }
        /* Optional: reduce padding at very top */
        .block-container { padding-top: 0.5rem; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Header (banner with logo or fallback title) ---
if LOGO_PATH.exists():
    st.markdown(
        f"""
        <div class="banner">
            <img src="file://{LOGO_PATH}" alt="Shop n Home Logo">
        </div>
        """,
        unsafe_allow_html=True
    )
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
