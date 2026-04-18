from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrderStatus(StrEnum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


order_status_enum = Enum(
    OrderStatus,
    name="order_status",
    values_callable=lambda enum_class: [status.value for status in enum_class],
)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_phone: Mapped[str] = mapped_column(String(32))
    customer_city: Mapped[str] = mapped_column(String(120))
    customer_street: Mapped[str] = mapped_column(String(120))
    customer_house: Mapped[str] = mapped_column(String(32))
    customer_building: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        order_status_enum,
        default=OrderStatus.CREATED,
        server_default=OrderStatus.CREATED.value,
    )
    cancellation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("product_price >= 0", name="order_items_product_price_check"),
        CheckConstraint("quantity > 0", name="order_items_quantity_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(Integer)
    product_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="items")


@event.listens_for(Order, "before_update")
def update_order_timestamp(mapper, connection, target):
    target.updated_at = datetime.now()
