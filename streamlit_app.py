# streamlit_app.py
import streamlit as st
from pathlib import Path
import base64
from pages import household, cookbook, food_plan, shopping_list  # each must expose render()

# --- Paths ---
APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "pictures" / "Shop_n_Home.png"  # <-- JPEG logo

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
            background-color: white;   /* white banner */
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
            text-align: center;        /* center content */
        }
        .sticky-banner img {
            max-width: 300px;          /* control logo size */
            max-height: auto;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Convert image to base64 for embedding ---
def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- Header ---
if LOGO_PATH.exists():
    logo_base64 = get_base64_image(LOGO_PATH)
    st.markdown(
        f"""
        <div class="sticky-banner">
            <img src="data:image/jpeg;base64,{logo_base64}" alt="Shop n Home Logo">
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







