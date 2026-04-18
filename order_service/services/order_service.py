from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import OrderNotFoundError, ProductNotFoundError
from models import Order, OrderItem, OrderStatus
from schemas import OrderCancel, OrderContainingProductRead, OrderCreate, OrderRead
from services._helpers import _serialize_orders, fetch_products_by_ids
import repositories.order_repository as order_repo


async def list_orders(
    session: AsyncSession,
    limit: int,
    offset: int,
    customer_phone: Optional[str],
    status: Optional[OrderStatus],
    min_amount: Optional[Decimal],
    max_amount: Optional[Decimal],
    order_by: str,
) -> list[OrderRead]:
    orders = await order_repo.get_orders(
        session=session,
        limit=limit,
        offset=offset,
        customer_phone=customer_phone,
        status=status,
        min_amount=min_amount,
        max_amount=max_amount,
        order_by=order_by,
    )
    return await _serialize_orders(orders)


async def get_order(session: AsyncSession, order_id: int) -> OrderRead:
    order = await order_repo.get_order_by_id(session, order_id)
    if order is None:
        raise OrderNotFoundError("Order not found")
    return (await _serialize_orders([order]))[0]


async def list_orders_by_product(
    session: AsyncSession, product_id: int
) -> list[OrderContainingProductRead]:
    orders = await order_repo.get_orders_by_product_id(session, product_id)
    return [
        OrderContainingProductRead(
            id=order.id,
            status=order.status,
            created_at=order.created_at,
        )
        for order in orders
    ]


async def create_order(session: AsyncSession, payload: OrderCreate) -> OrderRead:
    product_ids = [item.product_id for item in payload.items]
    products_by_id = await fetch_products_by_ids(product_ids)

    missing_product_ids = sorted(set(product_ids) - set(products_by_id))
    if missing_product_ids:
        raise ProductNotFoundError(
            f"Products not found: {', '.join(map(str, missing_product_ids))}"
        )

    order = Order(
        customer_phone=payload.customer_phone,
        customer_city=payload.customer_city,
        customer_street=payload.customer_street,
        customer_house=payload.customer_house,
        customer_building=payload.customer_building,
    )
    order.items = [
        OrderItem(
            product_id=item.product_id,
            product_price=products_by_id[item.product_id].price,
            quantity=item.quantity,
        )
        for item in payload.items
    ]

    saved_order = await order_repo.save_order(session, order)
    return await get_order(session, saved_order.id)


async def update_order_status(
    session: AsyncSession, order_id: int, new_status: OrderStatus
) -> OrderRead:
    order = await order_repo.get_order_for_update(session, order_id)
    if order is None:
        raise OrderNotFoundError("Order not found")

    order.status = new_status
    if new_status != OrderStatus.CANCELLED:
        order.cancellation_note = None

    await session.commit()
    return await get_order(session, order_id)


async def cancel_order(
    session: AsyncSession, order_id: int, payload: OrderCancel
) -> OrderRead:
    order = await order_repo.get_order_for_update(session, order_id)
    if order is None:
        raise OrderNotFoundError("Order not found")

    order.status = OrderStatus.CANCELLED
    order.cancellation_note = payload.cancellation_note
    await session.commit()
    return await get_order(session, order_id)
