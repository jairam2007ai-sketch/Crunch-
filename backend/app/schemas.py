"""Request shapes. Every text field is length-limited and cleaned of invisible control
characters and direction-flipping characters that can disguise what text says."""
import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

PHONE_RE = re.compile(r"^[6-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_RE = r"^[a-z0-9_-]{1,32}$"
# C0 controls (except tab/newline), DEL, zero-width and bidirectional override characters
_HIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")


def clean_line(v: str) -> str:
    """One line of text: hidden characters removed, runs of spaces/tabs/newlines collapsed."""
    return " ".join(_HIDDEN.sub("", v).split())


def clean_block(v: str) -> str:
    """Multi-line text: hidden characters removed, line breaks kept, edges trimmed."""
    text = _HIDDEN.sub("", v).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(" ".join(line.split()) for line in text.split("\n")).strip()


Line = Annotated[str, AfterValidator(clean_line)]
Block = Annotated[str, AfterValidator(clean_block)]
Code = Annotated[str, Field(pattern=CODE_RE)]


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
    product_code: Code
    quantity: int = Field(default=1, ge=1, le=20)
    base: Code
    toppings: list[Code] = Field(default_factory=list, max_length=6)
    sauces: list[Code] = Field(default_factory=list, max_length=6)
    seasonings: list[Code] = Field(default_factory=list, max_length=6)


class OnlineOrderIn(BaseModel):
    customer_name: Line = Field(max_length=40)
    customer_phone: str = Field(max_length=20)
    items: list[SelectionIn] = Field(min_length=1, max_length=10)
    payment_method: Literal["upi", "pay_at_cart"]
    note: Line = Field(default="", max_length=200)

    @field_validator("customer_name")
    @classmethod
    def name_present(cls, v: str) -> str:
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
    customer_name: Line = Field(default="", max_length=40)
    upi_reference: Line = Field(default="", max_length=60)
    note: Line = Field(default="", max_length=200)


class StatusIn(BaseModel):
    status: Literal["placed", "preparing", "ready", "completed", "cancelled"]
    reason: Line = Field(default="", max_length=200)


class PayIn(BaseModel):
    method: Literal["cash", "upi"]
    reference: Line = Field(default="", max_length=60)


class RefundIn(BaseModel):
    order_id: int = Field(ge=1)
    amount: int = Field(ge=1, le=100000)
    method: Literal["cash", "upi"]
    reason: Line = Field(max_length=200)

    @field_validator("reason")
    @classmethod
    def reason_present(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Say briefly why the refund is needed.")
        return v


class DecisionIn(BaseModel):
    note: Line = Field(default="", max_length=200)


class StockAdjustIn(BaseModel):
    type: Literal["in", "waste", "count"]
    quantity: float = Field(ge=0, le=100000, allow_inf_nan=False)
    note: Line = Field(default="", max_length=200)


class IngredientUpdateIn(BaseModel):
    name: Line | None = Field(default=None, min_length=1, max_length=60)
    note: Line | None = Field(default=None, max_length=60)
    is_active: bool | None = None
    low_stock_at: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    track_stock: bool | None = None


class ProductUpdateIn(BaseModel):
    price: int | None = Field(default=None, ge=1, le=5000)
    cost: int | None = Field(default=None, ge=0, le=5000)
    is_active: bool | None = None
    description: Line | None = Field(default=None, max_length=200)


class UserCreateIn(BaseModel):
    name: Line = Field(min_length=2, max_length=80)
    email: str = Field(max_length=160)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["seller", "owner"] = "seller"

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v) or _HIDDEN.search(v):
            raise ValueError("Enter a valid email address.")
        return v


class UserUpdateIn(BaseModel):
    name: Line | None = Field(default=None, min_length=2, max_length=80)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


class SettingsIn(BaseModel):
    shop_name: Line | None = Field(default=None, min_length=2, max_length=80)
    is_open: bool | None = None
    upi_id: str | None = Field(default=None, max_length=80)
    upi_name: Line | None = Field(default=None, max_length=80)
    pickup_note: Block | None = Field(default=None, max_length=300)
    daily_target_min: int | None = Field(default=None, ge=0, le=10000)
    daily_target_max: int | None = Field(default=None, ge=0, le=10000)

    @field_validator("upi_id")
    @classmethod
    def check_upi(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v and not re.fullmatch(r"[A-Za-z0-9._-]{2,64}@[A-Za-z]{2,32}", v):
            raise ValueError("A UPI ID looks like name@bank.")
        return v


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Block = Field(max_length=4000)


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)


class ConfirmIn(BaseModel):
    action_token: str = Field(max_length=4000)
