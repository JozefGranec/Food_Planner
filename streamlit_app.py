from pages import cookbook, food_plan, shopping_list

tab1, tab2, tab3 = st.tabs(["Cook Book", "Food Plan", "Shopping List"])
with tab1:
    cookbook.render()
with tab2:
    food_plan.render()
with tab3:
    shopping_list.render()
