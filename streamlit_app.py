import streamlit as st
import pandas as pd

st.set_page_config(page_title="Food Planner", page_icon="🍽️", layout="centered")

st.title("🍽️ Weekly Food Planner")
st.write("Plan your meals for the week and automatically generate a shopping list.")

# Days of the week
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Create a dictionary to store meals
meals = {}

st.subheader("Enter your meals for each day")
for day in days:
    meals[day] = st.text_input(f"{day}:", placeholder="e.g., Pasta with tomato sauce")

# Convert to DataFrame for display
df = pd.DataFrame(list(meals.items()), columns=["Day", "Meal"])

st.subheader("📅 Your Weekly Plan")
st.table(df)

# Generate shopping list (very simple split by commas/space)
shopping_list = []
for meal in meals.values():
    if meal:
        shopping_list.extend([item.strip() for item in meal.split(",")])

shopping_list = sorted(set(shopping_list))

if st.button("Generate Shopping List"):
    st.subheader("🛒 Shopping List")
    for item in shopping_list:
        st.write(f"- {item}")