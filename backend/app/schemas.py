import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_RE = re.compile(r"^[6-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SelectionIn(BaseModel):
    product_code: str = Field(max_length=32)
    quantity: int = Field(default=1, ge=1, le=20)
    base: str = Field(max_length=32)
    toppings: list[str] = Field(default_factory=list, max_length=6)
    sauces: list[str] = Field(default_factory=list, max_length=6)
    seasonings: list[str] = Field(default_factory=list, max_length=6)


class OnlineOrderIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=40)
    customer_phone: str
    items: list[SelectionIn] = Field(min_length=1, max_length=10)
    payment_method: Literal["upi", "pay_at_cart"]
    note: str = Field(default="", max_length=200)

    @field_validator("customer_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Please enter your name.")
        return v

    @field_validator("customer_phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if not PHONE_RE.match(digits):
            raise ValueError("Enter a 10-digit mobile number.")
        return digits


class CounterOrderIn(BaseModel):
    items: list[SelectionIn] = Field(min_length=1, max_length=20)
    payment_method: Literal["cash", "upi"]
    paid: bool = True
    customer_name: str = Field(default="", max_length=40)
    upi_reference: str = Field(default="", max_length=60)
    note: str = Field(default="", max_length=200)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_code: str
    product_name: str
    quantity: int
    unit_price: int
    total: int
    selections: dict


class OrderOut(BaseModel):
    id: int
    number: int
    business_date: str
    source: str
    status: str
    customer_name: str
    customer_phone: str
    note: str
    total_amount: int
    payment_method: str
    payment_status: str
    refunded_amount: int
    cancel_reason: str
    created_at: str | None
    updated_at: str | None
    created_by_name: str | None = None
    items: list[OrderItemOut]


class TrackOut(BaseModel):
    number: int
    business_date: str
    status: str
    customer_name: str
    total_amount: int
    payment_method: str
    payment_status: str
    created_at: str | None
    items: list[OrderItemOut]
    ahead: int
    can_cancel: bool
    upi_link: str | None
    upi_id: str
    pickup_note: str


class StatusIn(BaseModel):
    status: Literal["placed", "preparing", "ready", "completed", "cancelled"]
    reason: str = Field(default="", max_length=200)


class PayIn(BaseModel):
    method: Literal["cash", "upi"]
    reference: str = Field(default="", max_length=60)


class RefundIn(BaseModel):
    order_id: int
    amount: int = Field(ge=1)
    method: Literal["cash", "upi"]
    reason: str = Field(min_length=3, max_length=200)


class DecisionIn(BaseModel):
    note: str = Field(default="", max_length=200)


class StockAdjustIn(BaseModel):
    type: Literal["in", "waste", "count"]
    quantity: float = Field(ge=0, le=100000)
    note: str = Field(default="", max_length=200)


class IngredientUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    note: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None
    low_stock_at: float | None = Field(default=None, ge=0, le=100000)
    track_stock: bool | None = None


class ProductUpdateIn(BaseModel):
    price: int | None = Field(default=None, ge=1, le=5000)
    cost: int | None = Field(default=None, ge=0, le=5000)
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=200)


class UserCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=160)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["seller", "owner"] = "seller"

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v


class UserUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


class SettingsIn(BaseModel):
    shop_name: str | None = Field(default=None, min_length=2, max_length=80)
    is_open: bool | None = None
    upi_id: str | None = Field(default=None, max_length=80)
    upi_name: str | None = Field(default=None, max_length=80)
    pickup_note: str | None = Field(default=None, max_length=300)
    daily_target_min: int | None = Field(default=None, ge=0, le=10000)
    daily_target_max: int | None = Field(default=None, ge=0, le=10000)

    @field_validator("upi_id")
    @classmethod
    def check_upi(cls, v: str | None) -> str | None:
        if v and not re.match(r"^[\w.\-]{2,}@[a-zA-Z]{2,}$", v.strip()):
            raise ValueError("A UPI ID looks like name@bank.")
        return v.strip() if v else v


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)


class ConfirmIn(BaseModel):
    action_token: str = Field(max_length=4000)
