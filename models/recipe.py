# models/recipe.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import datetime as dt

class Ingredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id", index=True)
    name: str = Field(index=True)
    amount: float = 0.0
    unit: str = "pcs"

class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    instructions: str
    image_b64: Optional[str] = None  # MVP: store small images; can switch to object storage later
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, nullable=False)

    ingredients: List[Ingredient] = Relationship(
        back_populates=None,
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}  # delete ingredients when recipe is removed
    )
