from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_phone: str = Field(min_length=1, max_length=32)
    customer_city: str = Field(min_length=1, max_length=120)
    customer_street: str = Field(min_length=1, max_length=120)
    customer_house: str = Field(min_length=1, max_length=32)
    customer_building: str | None = Field(default=None, max_length=32)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderCancel(BaseModel):
    cancellation_note: str = Field(min_length=1)


class ProductLookupRead(BaseModel):
    id: int
    name: str
    price: Decimal
    stock: int
    images: list[dict] = Field(default_factory=list)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    price: Decimal
    quantity: int
    created_at: datetime
    name: str
    stock: int
    image_url: str | None


class OrderContainingProductRead(BaseModel):
    id: int
    status: OrderStatus
    created_at: datetime


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_phone: str
    customer_city: str
    customer_street: str
    customer_house: str
    customer_building: str | None
    status: OrderStatus
    cancellation_note: str | None
    created_at: datetime
    updated_at: datetime
    total_amount: Decimal
    items: list[OrderItemRead]

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if data.get("cancellation_note") is None:
            data.pop("cancellation_note", None)
        return data
