"""Database tables. Money is stored in whole rupees; times are stored as naive UTC."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLES = ("owner", "seller")
ORDER_STATUSES = ("placed", "preparing", "ready", "completed", "cancelled")
PAYMENT_STATUSES = ("unpaid", "paid", "partially_refunded", "refunded")
INGREDIENT_CATEGORIES = ("base", "topping", "sauce", "seasoning", "extra", "packaging")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Bumped on password change or turn-off: every sign-in issued before stops working.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Product(Base):
    """A packet size on the menu: Regular or Loaded."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[int] = mapped_column(Integer)
    cost: Mapped[int] = mapped_column(Integer, default=0)  # owner's estimate of cost per packet
    toppings_allowed: Mapped[int] = mapped_column(Integer)
    sauces_allowed: Mapped[int] = mapped_column(Integer)
    seasonings_allowed: Mapped[int] = mapped_column(Integer)
    includes_cheese: Mapped[bool] = mapped_column(Boolean, default=False)
    base_portions: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Ingredient(Base):
    """Something that goes into a packet. Stock is counted in portions."""
    __tablename__ = "ingredients"
    __table_args__ = (UniqueConstraint("category", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(16), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(60))
    note: Mapped[str] = mapped_column(String(60), default="")
    color: Mapped[str] = mapped_column(String(9), default="#cccccc")
    stock_qty: Mapped[float] = mapped_column(Float, default=0)
    # Tracking switches on with the first stock entry, so a new shop can sell before counting.
    track_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    low_stock_at: Mapped[float] = mapped_column(Float, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("business_date", "daily_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_date: Mapped[str] = mapped_column(String(10), index=True)  # shop-local YYYY-MM-DD
    daily_number: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # counter | online
    status: Mapped[str] = mapped_column(String(16), default="placed", index=True)
    customer_name: Mapped[str] = mapped_column(String(60), default="")
    customer_phone: Mapped[str] = mapped_column(String(15), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    total_amount: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(16))  # cash | upi | pay_at_cart
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    refunded_amount: Mapped[int] = mapped_column(Integer, default=0)
    tracking_token: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    cancel_reason: Mapped[str] = mapped_column(String(200), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin", order_by="OrderItem.id"
    )
    payments: Mapped[list["Payment"]] = relationship(lazy="selectin", order_by="Payment.id")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_code: Mapped[str] = mapped_column(String(32))
    product_name: Mapped[str] = mapped_column(String(60))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    # {"base": "potato", "toppings": [...], "sauces": [...], "seasonings": [...], "cheese": bool}
    selections: Mapped[dict] = mapped_column(JSON)

    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(16))  # cash | upi
    amount: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(60), default="")
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(16))  # cash | upi
    reason: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending | approved | rejected
    decision_note: Mapped[str] = mapped_column(String(200), default="")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped[Order] = relationship(lazy="joined")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), index=True)
    type: Mapped[str] = mapped_column(String(12))  # in | out | return | waste | count
    quantity: Mapped[float] = mapped_column(Float)
    balance_after: Mapped[float] = mapped_column(Float)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(48), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_name: Mapped[str] = mapped_column(String(80), default="Customize Your Crunch")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    upi_name: Mapped[str] = mapped_column(String(80), default="")
    pickup_note: Mapped[str] = mapped_column(Text, default="")
    daily_target_min: Mapped[int] = mapped_column(Integer, default=20)
    daily_target_max: Mapped[int] = mapped_column(Integer, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
