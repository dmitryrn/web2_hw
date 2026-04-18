from decimal import Decimal

import httpx

from exceptions import ProductNotFoundError, ProductServiceUnavailableError
from models import Order, OrderItem
from schemas import OrderItemRead, OrderRead, ProductLookupRead
from settings import settings


async def fetch_products_by_ids(product_ids: list[int]) -> dict[int, ProductLookupRead]:
    unique_product_ids = sorted(set(product_ids))
    if not unique_product_ids:
        return {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(
                f"{settings.product_service_url}/products/lookup",
                json={"ids": unique_product_ids},
            )
        except httpx.HTTPError as exc:
            raise ProductServiceUnavailableError("Product service unavailable") from exc

    if response.status_code != 200:
        raise ProductServiceUnavailableError("Product service unavailable")

    products = [ProductLookupRead.model_validate(item) for item in response.json()]
    return {product.id: product for product in products}


async def _serialize_orders(orders: list[Order]) -> list[OrderRead]:
    products_by_id = await fetch_products_by_ids(
        [item.product_id for order in orders for item in order.items]
    )
    missing_product_ids = sorted(
        {item.product_id for order in orders for item in order.items}
        - set(products_by_id)
    )
    if missing_product_ids:
        raise ProductNotFoundError(
            f"Product data unavailable: {', '.join(map(str, missing_product_ids))}"
        )

    return [
        OrderRead(
            id=order.id,
            customer_phone=order.customer_phone,
            customer_city=order.customer_city,
            customer_street=order.customer_street,
            customer_house=order.customer_house,
            customer_building=order.customer_building,
            status=order.status,
            cancellation_note=order.cancellation_note,
            created_at=order.created_at,
            updated_at=order.updated_at,
            total_amount=Decimal(
                sum(item.product_price * item.quantity for item in order.items)
            ),
            items=[
                OrderItemRead(
                    id=item.id,
                    price=item.product_price,
                    quantity=item.quantity,
                    created_at=item.created_at,
                    name=products_by_id[item.product_id].name,
                    stock=products_by_id[item.product_id].stock,
                )
                for item in order.items
            ],
        )
        for order in orders
    ]
