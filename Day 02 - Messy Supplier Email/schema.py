"""
Day 2 / 30 - the schema IS the specification.

Everything the model is allowed to return is defined here. The prompt describes
intent; this file enforces it. When they disagree, this file wins.
"""

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def clean_decimal(v):
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    if isinstance(v, str):
        cleaned = (
            v.replace(",", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .replace("/-", "")
            .replace("$", "")
            .replace("USD", "")
            .strip()
        )
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except Exception:
            return v
    return v


class LineItem(BaseModel):
    sku: Optional[str] = Field(
        None, description="Supplier SKU exactly as written. null if not stated."
    )
    description: str = Field(description="What the item is, in the email's own words.")
    quantity: int = Field(description="Resolved to a number. '2 dozen' -> 24.")
    unit_price: Optional[Decimal] = Field(
        None, description="Price per unit. null if the email does not state one."
    )

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be greater than 0")
        return v

    @field_validator("unit_price", mode="before")
    @classmethod
    def parse_unit_price(cls, v):
        return clean_decimal(v)

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("unit_price must be greater than 0")
        return v


class PurchaseOrder(BaseModel):
    is_purchase_order: bool = Field(
        description="False if this email is not an order at all (a query, a complaint, "
        "a follow-up). If false, every other field must be null or empty."
    )
    supplier_name: Optional[str] = None
    po_number: Optional[str] = Field(
        None, description="null if the email does not contain one. Do not invent one."
    )
    order_date: Optional[date] = None
    expected_delivery: Optional[date] = Field(
        None,
        description="Resolve relative dates ('next Friday', 'end of month') against "
        "the received date given in the prompt. null if genuinely unstated.",
    )
    currency: Optional[Literal["INR", "USD", "EUR", "GBP"]] = None
    line_items: list[LineItem] = Field(default_factory=list)
    stated_total: Optional[Decimal] = Field(
        None,
        description="The total as written in the email. Do NOT calculate this "
        "yourself. null if the email states no total.",
    )
    ambiguities: list[str] = Field(
        default_factory=list,
        description="Anything you had to guess at, or that a human should check. "
        "An empty list means you are confident in every field above.",
    )

    @field_validator("stated_total", mode="before")
    @classmethod
    def parse_stated_total(cls, v):
        return clean_decimal(v)

    @model_validator(mode="after")
    def check_consistency(self) -> "PurchaseOrder":
        if not self.is_purchase_order:
            if self.line_items:
                raise ValueError(
                    "is_purchase_order is false but line_items were returned. "
                    "If this is not an order, return no line items."
                )
            return self

        if not self.line_items:
            raise ValueError(
                "is_purchase_order is true but no line items were extracted."
            )
        if self.order_date and self.expected_delivery:
            if self.expected_delivery < self.order_date:
                raise ValueError(
                    f"expected_delivery ({self.expected_delivery}) is before "
                    f"order_date ({self.order_date}). Re-read the dates."
                )
        if any(i.unit_price for i in self.line_items) and not self.currency:
            raise ValueError("Prices were extracted but currency is null.")
        return self
