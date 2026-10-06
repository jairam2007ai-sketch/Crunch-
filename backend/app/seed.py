"""The Crunch menu, from the shop's own menu board. Safe to run on every start."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Ingredient, Product, ShopSettings

PRODUCTS = [
    dict(code="regular", name="Regular", description="Regular portion, 2 toppings, 1 sauce, 1 seasoning",
         price=49, toppings_allowed=2, sauces_allowed=1, seasonings_allowed=1, includes_cheese=False,
         base_portions=1.0, sort=1),
    dict(code="loaded", name="Loaded", description="Larger portion, 3 toppings, 2 sauces, 2 seasonings, cheese",
         price=69, toppings_allowed=3, sauces_allowed=2, seasonings_allowed=2, includes_cheese=True,
         base_portions=1.5, sort=2),
]

INGREDIENTS = [
    ("base", "potato", "Potato chips", "Classic", "#F0C75E"),
    ("base", "masala", "Masala chips", "Spicy", "#E5853A"),
    ("base", "kurkure", "Kurkure", "Crunchy", "#F29634"),
    ("base", "bingo", "Bingo chips", "Flavourful", "#F2B04C"),
    ("topping", "onion", "Onion", "", "#A9467C"),
    ("topping", "tomato", "Tomato", "", "#D63A2C"),
    ("topping", "corn", "Corn", "", "#F7CF40"),
    ("topping", "cucumber", "Cucumber", "", "#86B84B"),
    ("topping", "coriander", "Coriander", "", "#2E8B3C"),
    ("sauce", "garlic", "Garlic mayo", "", "#F3EAD0"),
    ("sauce", "tandoori", "Tandoori mayo", "", "#EC7B3D"),
    ("sauce", "periperi", "Peri-peri sauce", "", "#CB2A1E"),
    ("seasoning", "oregano", "Oregano", "", "#56692B"),
    ("seasoning", "chilli", "Chilli flakes", "", "#B0241B"),
    ("seasoning", "periperi", "Peri-peri", "", "#D8452A"),
    ("seasoning", "tandoori", "Tandoori", "", "#C24E28"),
    ("seasoning", "chaat", "Chaat masala", "", "#74492A"),
    ("extra", "cheese", "Cheese", "Loaded only", "#FFE27D"),
    ("packaging", "packet", "Packets", "Printed pouch + sticker", "#F5C211"),
]


def ensure_seed(db: Session) -> None:
    if not db.scalar(select(Product.id).limit(1)):
        for p in PRODUCTS:
            db.add(Product(**p))
    if not db.scalar(select(Ingredient.id).limit(1)):
        for i, (cat, code, name, note, color) in enumerate(INGREDIENTS):
            db.add(Ingredient(category=cat, code=code, name=name, note=note, color=color, sort=i,
                              low_stock_at=50 if cat == "packaging" else 10))
    if not db.get(ShopSettings, 1):
        db.add(ShopSettings(id=1))
    db.commit()
