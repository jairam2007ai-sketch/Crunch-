"""Stock, counted in portions. Sellers record deliveries and waste; the owner can set an exact count."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import audit, require_owner, require_staff
from ..models import Ingredient, InventoryTransaction, User
from ..schemas import IngredientUpdateIn, StockAdjustIn
from ..services.orders import user_names
from ..services.reports import inventory_status
from ..timeutil import iso_utc

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/inventory")
def list_stock(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return inventory_status(db)


def _ingredient(db: Session, ingredient_id: int) -> Ingredient:
    ing = db.get(Ingredient, ingredient_id)
    if not ing:
        raise HTTPException(404, "Ingredient not found.")
    return ing


@router.post("/inventory/{ingredient_id}/adjust")
def adjust(ingredient_id: int, body: StockAdjustIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    ing = _ingredient(db, ingredient_id)
    old = ing.stock_qty
    if body.type == "count" and user.role != "owner":
        raise HTTPException(403, "Only the owner can overwrite a stock count. Record a delivery or waste instead.")
    if body.type == "in":
        if body.quantity <= 0:
            raise HTTPException(400, "Enter how many portions came in.")
        ing.stock_qty = round(old + body.quantity, 3)
        change = body.quantity
    elif body.type == "waste":
        if body.quantity <= 0:
            raise HTTPException(400, "Enter how many portions were thrown away.")
        if ing.track_stock and body.quantity > old + 1e-9:
            raise HTTPException(409, f"Only {old:g} portions of {ing.name} are in stock.")
        ing.stock_qty = round(max(0.0, old - body.quantity), 3)
        change = -body.quantity
    else:
        ing.stock_qty = round(body.quantity, 3)
        change = round(body.quantity - old, 3)
    ing.track_stock = True
    db.add(InventoryTransaction(ingredient_id=ing.id, type=body.type, quantity=change, balance_after=ing.stock_qty,
                                note=body.note, created_by=user.id))
    audit(db, user, f"stock.{body.type}", "ingredient", ing.id, old={"stock": old}, new={"stock": ing.stock_qty, "note": body.note})
    db.commit()
    return next(i for i in inventory_status(db) if i["id"] == ing.id)


@router.get("/inventory/{ingredient_id}/history")
def history(ingredient_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    _ingredient(db, ingredient_id)
    names = user_names(db)
    rows = db.scalars(select(InventoryTransaction).where(InventoryTransaction.ingredient_id == ingredient_id)
                      .order_by(InventoryTransaction.created_at.desc()).limit(40))
    return [{"id": t.id, "type": t.type, "quantity": t.quantity, "balance_after": t.balance_after, "note": t.note,
             "by": names.get(t.created_by), "order_id": t.order_id, "created_at": iso_utc(t.created_at)} for t in rows]


@router.patch("/ingredients/{ingredient_id}")
def update_ingredient(ingredient_id: int, body: IngredientUpdateIn, db: Session = Depends(get_db),
                      user: User = Depends(require_owner)):
    ing = _ingredient(db, ingredient_id)
    changes = body.model_dump(exclude_none=True)
    old = {k: getattr(ing, k) for k in changes}
    for k, v in changes.items():
        setattr(ing, k, v)
    audit(db, user, "ingredient.update", "ingredient", ing.id, old=old, new=changes)
    db.commit()
    return next(i for i in inventory_status(db) if i["id"] == ing.id)
