from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date
    transaction_type: Literal["income", "expense"]


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date | None = None
    transaction_type: Literal["income", "expense"] | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    category: str
    description: str | None
    transaction_date: date
    transaction_type: str