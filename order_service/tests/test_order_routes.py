import asyncio
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("PRODUCT_SERVICE_URL", "http://localhost:8000")

import main as app_module
from db import engine as db_engine, get_session as db_get_session
from models import Base, OrderStatus
from schemas import ProductLookupRead


def product_data(
    id: int, price: str, *, name: str | None = None, stock: int = 5
) -> ProductLookupRead:
    return ProductLookupRead(
        id=id,
        name=name or f"Product {id}",
        price=price,
        stock=stock,
    )


def create_order(client: TestClient, **overrides: object) -> dict:
    response = client.post(
        "/orders",
        json={
            "customer_phone": "+1234567890",
            "customer_city": "Almaty",
            "customer_street": "Satpayev",
            "customer_house": "10A",
            "customer_building": "2",
            "items": [{"product_id": 1, "quantity": 2}],
            **overrides,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def session_factory() -> Iterator[async_sessionmaker[AsyncSession]]:
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_session():
        async with session_factory() as session:
            yield session

    async def prepare_db() -> None:
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    original_engine = db_engine
    import db

    db.engine = test_engine
    app_module.app.dependency_overrides[db_get_session] = override_get_session

    try:
        asyncio.run(prepare_db())
        yield session_factory
    finally:
        app_module.app.dependency_overrides.clear()
        db.engine = original_engine
        asyncio.run(test_engine.dispose())


@pytest.fixture
def product_catalog(monkeypatch: pytest.MonkeyPatch) -> dict[int, ProductLookupRead]:
    catalog: dict[int, ProductLookupRead] = {}

    async def fake_fetch_products_by_ids(
        product_ids: list[int],
    ) -> dict[int, ProductLookupRead]:
        return {
            product_id: catalog[product_id]
            for product_id in product_ids
            if product_id in catalog
        }

    import services._helpers as helpers_module

    monkeypatch.setattr(
        helpers_module, "fetch_products_by_ids", fake_fetch_products_by_ids
    )
    import services.order_service as order_service_module

    monkeypatch.setattr(
        order_service_module, "fetch_products_by_ids", fake_fetch_products_by_ids
    )
    return catalog


@pytest.fixture
def client(
    session_factory: async_sessionmaker[AsyncSession],
    product_catalog: dict[int, ProductLookupRead],
) -> Iterator[TestClient]:
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_list_orders_returns_empty_list_when_no_orders(client: TestClient) -> None:
    response = client.get("/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_create_order_happy_path(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99", name="Cooler Master 500", stock=7)
    product_catalog[2] = product_data(2, "49.50", name="Fan 120", stock=11)

    response = client.post(
        "/orders",
        json={
            "customer_phone": "+1234567890",
            "customer_city": "Almaty",
            "customer_street": "Satpayev",
            "customer_house": "10A",
            "customer_building": "2",
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 2, "quantity": 3},
            ],
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "customer_phone": "+1234567890",
        "customer_city": "Almaty",
        "customer_street": "Satpayev",
        "customer_house": "10A",
        "customer_building": "2",
        "status": "created",
        "cancellation_note": None,
        "created_at": response.json()["created_at"],
        "updated_at": response.json()["updated_at"],
        "total_amount": "548.48",
        "items": [
            {
                "id": 1,
                "price": "199.99",
                "quantity": 2,
                "created_at": response.json()["items"][0]["created_at"],
                "name": "Cooler Master 500",
                "stock": 7,
            },
            {
                "id": 2,
                "price": "49.50",
                "quantity": 3,
                "created_at": response.json()["items"][1]["created_at"],
                "name": "Fan 120",
                "stock": 11,
            },
        ],
    }


def test_list_orders_happy_path(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    product_catalog[2] = product_data(2, "49.50")
    first_order = create_order(client)
    second_order = create_order(
        client,
        customer_phone="+77001234567",
        customer_city="Astana",
        customer_street="Mangilik El",
        customer_house="15",
        customer_building=None,
        items=[{"product_id": 2, "quantity": 4}],
    )

    response = client.get("/orders")

    assert response.status_code == 200
    assert response.json() == [first_order, second_order]


def test_get_order_happy_path(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    created_order = create_order(client)

    response = client.get(f"/orders/{created_order['id']}")

    assert response.status_code == 200
    assert response.json() == created_order


def test_update_order_status_happy_path(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    created_order = create_order(client)

    response = client.patch(
        f"/orders/{created_order['id']}/status",
        json={"status": "confirmed"},
    )

    assert response.status_code == 200
    assert response.json() == {
        **created_order,
        "status": "confirmed",
        "updated_at": response.json()["updated_at"],
    }


def test_cancel_order_happy_path(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    created_order = create_order(client)

    response = client.patch(
        f"/orders/{created_order['id']}/cancel",
        json={"cancellation_note": "Customer changed their mind"},
    )

    assert response.status_code == 200
    assert response.json() == {
        **created_order,
        "status": "cancelled",
        "cancellation_note": "Customer changed their mind",
        "updated_at": response.json()["updated_at"],
    }


def test_create_order_returns_404_when_any_product_is_missing(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")

    response = client.post(
        "/orders",
        json={
            "customer_phone": "+1234567890",
            "customer_city": "Almaty",
            "customer_street": "Satpayev",
            "customer_house": "10A",
            "customer_building": "2",
            "items": [
                {"product_id": 1, "quantity": 1},
                {"product_id": 99, "quantity": 1},
            ],
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Products not found: 99"}


def test_get_order_returns_404_when_order_does_not_exist(client: TestClient) -> None:
    response = client.get("/orders/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}


def test_update_order_status_returns_404_when_order_does_not_exist(
    client: TestClient,
) -> None:
    response = client.patch("/orders/999/status", json={"status": "confirmed"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}


def test_cancel_order_returns_404_when_order_does_not_exist(client: TestClient) -> None:
    response = client.patch(
        "/orders/999/cancel",
        json={"cancellation_note": "Out of stock"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}


def test_update_order_status_clears_cancellation_note_when_reopened(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    created_order = create_order(client)

    cancel_response = client.patch(
        f"/orders/{created_order['id']}/cancel",
        json={"cancellation_note": "Duplicate order"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == OrderStatus.CANCELLED
    assert cancel_response.json()["cancellation_note"] == "Duplicate order"

    response = client.patch(
        f"/orders/{created_order['id']}/status",
        json={"status": "confirmed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["cancellation_note"] is None


def test_create_order_rejects_invalid_quantity(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")

    response = client.post(
        "/orders",
        json={
            "customer_phone": "+1234567890",
            "customer_city": "Almaty",
            "customer_street": "Satpayev",
            "customer_house": "10A",
            "customer_building": "2",
            "items": [{"product_id": 1, "quantity": 0}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "items", 0, "quantity"]


def test_update_order_status_rejects_invalid_status(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    created_order = create_order(client)

    response = client.patch(
        f"/orders/{created_order['id']}/status",
        json={"status": "packing"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "status"]


def test_cancel_order_requires_non_empty_cancellation_note(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    created_order = create_order(client)

    response = client.patch(
        f"/orders/{created_order['id']}/cancel",
        json={"cancellation_note": ""},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "cancellation_note"]


def test_list_orders_by_product_returns_matching_orders(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "199.99")
    product_catalog[2] = product_data(2, "49.50")
    first_order = create_order(client)
    create_order(client, items=[{"product_id": 2, "quantity": 1}])

    response = client.get("/orders/by-product/1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": first_order["id"],
            "status": "created",
            "created_at": first_order["created_at"],
        }
    ]


def test_list_orders_pagination(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    create_order(client)
    create_order(client)
    create_order(client)

    response = client.get("/orders?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get("/orders?limit=2&offset=2")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/orders?limit=2&offset=10")
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_list_orders_filter_by_customer_phone(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    order1 = create_order(client, customer_phone="+1111111111")
    create_order(client, customer_phone="+2222222222")

    response = client.get("/orders?customer_phone=%2B1111111111")
    assert response.status_code == 200
    assert response.json() == [order1]


def test_list_orders_filter_by_status(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    order1 = create_order(client)
    order2 = create_order(client)

    client.patch(f"/orders/{order2['id']}/status", json={"status": "confirmed"})

    response = client.get("/orders?status=created")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order1["id"]

    response = client.get("/orders?status=confirmed")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order2["id"]


def test_list_orders_filter_by_amount(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    product_catalog[2] = product_data(2, "50.00")
    order1 = create_order(client, items=[{"product_id": 1, "quantity": 1}])
    order2 = create_order(client, items=[{"product_id": 2, "quantity": 1}])

    response = client.get("/orders?min_amount=75")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order1["id"]

    response = client.get("/orders?max_amount=75")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order2["id"]

    response = client.get("/orders?min_amount=25&max_amount=75")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order2["id"]


def test_list_orders_order_by_updated_at(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    order1 = create_order(client)
    time.sleep(0.1)
    order2 = create_order(client)
    time.sleep(0.1)

    client.patch(f"/orders/{order1['id']}/status", json={"status": "confirmed"})

    response = client.get("/orders?order_by=-updated_at")
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [order1["id"], order2["id"]]

    response = client.get("/orders?order_by=updated_at")
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [order2["id"], order1["id"]]


def test_list_orders_order_by_total_amount(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    product_catalog[2] = product_data(2, "50.00")
    order1 = create_order(client, items=[{"product_id": 1, "quantity": 1}])
    order2 = create_order(client, items=[{"product_id": 2, "quantity": 1}])

    response = client.get("/orders?order_by=-total_amount")
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [order1["id"], order2["id"]]

    response = client.get("/orders?order_by=total_amount")
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [order2["id"], order1["id"]]


def test_list_orders_combined_filters(
    client: TestClient, product_catalog: dict[int, ProductLookupRead]
) -> None:
    product_catalog[1] = product_data(1, "100.00")
    product_catalog[2] = product_data(2, "50.00")
    order1 = create_order(
        client, customer_phone="+1111111111", items=[{"product_id": 1, "quantity": 1}]
    )
    create_order(
        client, customer_phone="+1111111111", items=[{"product_id": 2, "quantity": 1}]
    )
    create_order(
        client, customer_phone="+2222222222", items=[{"product_id": 1, "quantity": 1}]
    )

    client.patch(f"/orders/{order1['id']}/status", json={"status": "confirmed"})

    response = client.get(
        "/orders?customer_phone=%2B1111111111&status=confirmed&min_amount=75"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order1["id"]
