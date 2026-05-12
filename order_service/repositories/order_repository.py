from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Order, OrderItem, OrderStatus


def _orders_query() -> Select[tuple[Order]]:
    return select(Order).options(selectinload(Order.items)).order_by(Order.id)


async def get_orders(
    session: AsyncSession,
    limit: int,
    offset: int,
    customer_phone: str | None,
    status: OrderStatus | None,
    min_amount: float | None,
    max_amount: float | None,
    order_by: str,
) -> list[Order]:
    total_amount_subq = (
        select(
            OrderItem.order_id.label("order_id"),
            func.sum(OrderItem.product_price * OrderItem.quantity).label(
                "total_amount"
            ),
        )
        .group_by(OrderItem.order_id)
        .subquery()
    )

    query = (
        select(Order)
        .options(selectinload(Order.items))
        .join(total_amount_subq, total_amount_subq.c.order_id == Order.id)
    )

    if customer_phone:
        query = query.where(Order.customer_phone == customer_phone)
    if status:
        query = query.where(Order.status == status)
    if min_amount is not None:
        query = query.where(total_amount_subq.c.total_amount >= min_amount)
    if max_amount is not None:
        query = query.where(total_amount_subq.c.total_amount <= max_amount)

    direction = desc if order_by.startswith("-") else asc
    sort_field = order_by.lstrip("-")
    if sort_field == "total_amount":
        query = query.order_by(direction(total_amount_subq.c.total_amount), Order.id)
    else:
        query = query.order_by(direction(Order.updated_at), Order.id)

    result = await session.scalars(query.limit(limit).offset(offset))
    return list(result)


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    return await session.scalar(_orders_query().where(Order.id == order_id))


async def get_orders_by_product_id(
    session: AsyncSession, product_id: int
) -> list[Order]:
    result = await session.scalars(
        select(Order)
        .join(OrderItem)
        .where(OrderItem.product_id == product_id)
        .distinct()
        .order_by(Order.id)
    )
    return list(result)


async def save_order(session: AsyncSession, order: Order) -> Order:
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def get_order_for_update(session: AsyncSession, order_id: int) -> Order | None:
    return await session.get(Order, order_id)
