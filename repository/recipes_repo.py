# repository/recipes_repo.py
from typing import List, Optional
from sqlmodel import select, delete
from models.recipe import Recipe, Ingredient
from services.db import get_session
import streamlit as st

@st.cache_data(ttl=30, show_spinner=False)
def list_recipes_cached(q: str | None = None) -> List[Recipe]:
    with get_session() as s:
        stmt = select(Recipe).order_by(Recipe.created_at.desc())
        if q:
            ql = f"%{q.lower()}%"
            stmt = select(Recipe).where(Recipe.name.ilike(ql)).order_by(Recipe.created_at.desc())
        results = s.exec(stmt).all()
        # force-load ingredients relationship
        for r in results:
            _ = r.ingredients
        return results

def invalidate_recipe_cache():
    list_recipes_cached.clear()

def get_recipe(recipe_id: int) -> Optional[Recipe]:
    with get_session() as s:
        obj = s.get(Recipe, recipe_id)
        if obj:
            _ = obj.ingredients
        return obj

def create_recipe(name: str, instructions: str, ingredients: list[dict], image_b64: str | None) -> int:
    with get_session() as s:
        r = Recipe(name=name.strip(), instructions=instructions.strip(), image_b64=image_b64)
        s.add(r)
        s.flush()  # get r.id
        for ing in ingredients:
            s.add(Ingredient(
                recipe_id=r.id,
                name=ing["name"].strip(),
                amount=float(ing.get("amount") or 0.0),
                unit=(ing.get("unit") or "pcs").strip()
            ))
        s.commit()
        invalidate_recipe_cache()
        return r.id

def update_recipe(recipe_id: int, name: str, instructions: str, ingredients: list[dict], image_b64: str | None) -> bool:
    with get_session() as s:
        r = s.get(Recipe, recipe_id)
        if not r:
            return False
        r.name = name.strip()
        r.instructions = instructions.strip()
        if image_b64 is not None:
            r.image_b64 = image_b64
        # replace ingredients
        s.exec(delete(Ingredient).where(Ingredient.recipe_id == recipe_id))
        for ing in ingredients:
            s.add(Ingredient(
                recipe_id=recipe_id,
                name=ing["name"].strip(),
                amount=float(ing.get("amount") or 0.0),
                unit=(ing.get("unit") or "pcs").strip()
            ))
        s.commit()
        invalidate_recipe_cache()
        return True

def delete_recipe(recipe_id: int):
    with get_session() as s:
        r = s.get(Recipe, recipe_id)
        if not r:
            return
        s.delete(r)  # cascades to ingredients
        s.commit()
        invalidate_recipe_cache()
