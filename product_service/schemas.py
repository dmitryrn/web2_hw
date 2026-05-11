from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    image_url: str
    sort_order: int
    created_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0, default=0)
    description: str = Field(min_length=1)
    compatibility: str | None = None
    energy_rating: str | None = Field(default=None, max_length=32)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, min_length=1)
    compatibility: str | None = None
    energy_rating: str | None = Field(default=None, max_length=32)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    stock: int
    description: str
    compatibility: str | None
    energy_rating: str | None
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageRead] = Field(default_factory=list)


class ProductLookupRequest(BaseModel):
    ids: list[int] = Field(min_length=1)


class ProductLookupImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_url: str
    sort_order: int


class ProductLookupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    stock: int
    images: list[ProductLookupImageRead] = Field(default_factory=list)


class ProductImageCreate(BaseModel):
    image_url: str = Field(min_length=1)
    sort_order: int = Field(ge=0)


class ProductImageUpdate(BaseModel):
    image_url: str | None = Field(default=None, min_length=1)
    sort_order: int | None = Field(default=None, ge=0)
