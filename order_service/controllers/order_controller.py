from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from exceptions import (
    OrderNotFoundError,
    ProductNotFoundError,
    ProductServiceUnavailableError,
)
from models import OrderStatus
from schemas import (
    OrderCancel,
    OrderContainingProductRead,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
)
from security import require_jwt
from services import order_service as order_svc

router = APIRouter()


def _handle_service_error(exc: Exception) -> None:
    if isinstance(exc, OrderNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProductNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProductServiceUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    raise exc


@router.get("/orders", response_model=list[OrderRead], dependencies=[Depends(require_jwt)])
async def list_orders(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    customer_phone: Optional[str] = None,
    status: Optional[OrderStatus] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    order_by: str = Query("-updated_at", pattern="^-?(updated_at|total_amount)$"),
) -> list[OrderRead]:
    try:
        return await order_svc.list_orders(
            session=session,
            limit=limit,
            offset=offset,
            customer_phone=customer_phone,
            status=status,
            min_amount=min_amount,
            max_amount=max_amount,
            order_by=order_by,
        )
    except Exception as exc:
        _handle_service_error(exc)


@router.get("/orders/{id}", response_model=OrderRead, dependencies=[Depends(require_jwt)])
async def get_order(id: int, session: AsyncSession = Depends(get_session)) -> OrderRead:
    try:
        return await order_svc.get_order(session, id)
    except Exception as exc:
        _handle_service_error(exc)


@router.get(
    "/orders/by-product/{product_id}",
    response_model=list[OrderContainingProductRead],
    dependencies=[Depends(require_jwt)],
)
async def list_orders_by_product(
    product_id: int, session: AsyncSession = Depends(get_session)
) -> list[OrderContainingProductRead]:
    return await order_svc.list_orders_by_product(session, product_id)


@router.post("/orders", response_model=OrderRead, status_code=201)
async def create_order(
    payload: OrderCreate,
    session: AsyncSession = Depends(get_session),
) -> OrderRead:
    try:
        return await order_svc.create_order(session, payload)
    except Exception as exc:
        _handle_service_error(exc)


@router.patch(
    "/orders/{id}/status", response_model=OrderRead, dependencies=[Depends(require_jwt)]
)
async def update_order_status(
    id: int,
    payload: OrderStatusUpdate,
    session: AsyncSession = Depends(get_session),
) -> OrderRead:
    try:
        return await order_svc.update_order_status(session, id, payload.status)
    except Exception as exc:
        _handle_service_error(exc)


@router.patch(
    "/orders/{id}/cancel", response_model=OrderRead, dependencies=[Depends(require_jwt)]
)
async def cancel_order(
    id: int,
    payload: OrderCancel,
    session: AsyncSession = Depends(get_session),
) -> OrderRead:
    try:
        return await order_svc.cancel_order(session, id, payload)
    except Exception as exc:
        _handle_service_error(exc)
