import asyncio
import sys
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
os.environ.setdefault("ORDER_SERVICE_URL", "http://localhost:8001")

import db as db_module
import main as app_module
import services as services_module
from models import Base


def create_product(client: TestClient, **overrides: object) -> dict:
    response = client.post(
        "/products",
        json={
            "name": "Cooler Master 500",
            "price": "129.99",
            "stock": 7,
            "description": "Tower cooler",
            "compatibility": "AM4",
            "energy_rating": "A",
            **overrides,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_product_image(
    client: TestClient, product_id: int, *, image_url: str, sort_order: int
) -> dict:
    response = client.post(
        f"/products/{product_id}/images",
        json={
            "image_url": image_url,
            "sort_order": sort_order,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def orders_by_product(monkeypatch: pytest.MonkeyPatch) -> dict[int, list[dict]]:
    orders: dict[int, list[dict]] = {}

    async def fake_has_orders(self, product_id: int) -> bool:
        return bool(orders.get(product_id, []))

    monkeypatch.setattr(services_module.ProductService, "_has_orders", fake_has_orders)
    return orders


@pytest.fixture
def client(orders_by_product: dict[int, list[dict]]) -> Iterator[TestClient]:
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

    original_engine = db_module.engine
    db_module.engine = test_engine
    app_module.app.dependency_overrides[db_module.get_session] = override_get_session

    try:
        asyncio.run(prepare_db())
        with TestClient(app_module.app) as test_client:
            yield test_client
    finally:
        app_module.app.dependency_overrides.clear()
        db_module.engine = original_engine
        asyncio.run(test_engine.dispose())


def test_create_product_happy_path(client: TestClient) -> None:
    product = create_product(client)

    assert product == {
        "id": 1,
        "name": "Cooler Master 500",
        "price": "129.99",
        "stock": 7,
        "description": "Tower cooler",
        "compatibility": "AM4",
        "energy_rating": "A",
        "created_at": product["created_at"],
        "updated_at": product["updated_at"],
        "images": [],
    }


def test_list_products_happy_path(client: TestClient) -> None:
    first_product = create_product(client)
    second_product = create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == [first_product, second_product]


def test_list_products_with_pagination(client: TestClient) -> None:
    first_product = create_product(client)
    second_product = create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )
    third_product = create_product(
        client,
        name="DeepCool AK620",
        price="149.99",
        stock=0,
        description="Black edition cooler",
        compatibility="LGA1700",
        energy_rating="B",
    )

    response = client.get("/products", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert response.json() == [second_product]
    assert third_product["id"] == 3


def test_list_products_returns_empty_list_when_no_products(client: TestClient) -> None:
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_returns_empty_list_when_filters_match_nothing(
    client: TestClient,
) -> None:
    create_product(client)

    response = client.get(
        "/products",
        params={
            "compatibility": "LGA1700",
            "energy_rating": "Z",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_returns_empty_list_when_offset_is_beyond_range(
    client: TestClient,
) -> None:
    create_product(client)
    create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )

    response = client.get("/products", params={"offset": 10})

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_filters_by_compatibility_and_stock(client: TestClient) -> None:
    matching_product = create_product(client)
    create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )
    create_product(
        client,
        name="DeepCool AK620",
        price="149.99",
        stock=0,
        description="Black edition cooler",
        compatibility="AM4",
        energy_rating="B",
    )

    response = client.get(
        "/products",
        params={
            "compatibility": "AM4",
            "in_stock": "true",
        },
    )

    assert response.status_code == 200
    assert response.json() == [matching_product]


def test_list_products_filters_by_price_range_and_energy_rating(
    client: TestClient,
) -> None:
    create_product(client)
    matching_product = create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )
    create_product(
        client,
        name="DeepCool AK620",
        price="149.99",
        stock=8,
        description="Black edition cooler",
        compatibility="LGA1700",
        energy_rating="B",
    )

    response = client.get(
        "/products",
        params={
            "min_price": "150",
            "max_price": "250",
            "energy_rating": "A+",
        },
    )

    assert response.status_code == 200
    assert response.json() == [matching_product]


def test_list_products_filters_by_search(client: TestClient) -> None:
    create_product(client)
    matching_product = create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )

    response = client.get("/products", params={"search": "noctua"})

    assert response.status_code == 200
    assert response.json() == [matching_product]


def test_list_products_filters_by_multiple_conditions(client: TestClient) -> None:
    matching_product = create_product(client)
    create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )
    create_product(
        client,
        name="DeepCool AK620",
        price="149.99",
        stock=0,
        description="Black edition cooler",
        compatibility="AM4",
        energy_rating="A",
    )

    response = client.get(
        "/products",
        params={
            "compatibility": "AM4",
            "energy_rating": "A",
            "in_stock": "true",
        },
    )

    assert response.status_code == 200
    assert response.json() == [matching_product]


def test_get_product_happy_path(client: TestClient) -> None:
    product = create_product(client)

    response = client.get(f"/products/{product['id']}")

    assert response.status_code == 200
    assert response.json() == product


def test_lookup_products_returns_matching_products(client: TestClient) -> None:
    first_product = create_product(client)
    second_product = create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )

    response = client.post(
        "/products/lookup",
        json={"ids": [second_product["id"], 99, first_product["id"]]},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": first_product["id"],
            "name": first_product["name"],
            "price": first_product["price"],
            "stock": first_product["stock"],
        },
        {
            "id": second_product["id"],
            "name": second_product["name"],
            "price": second_product["price"],
            "stock": second_product["stock"],
        },
    ]


def test_get_product_includes_images(client: TestClient) -> None:
    product = create_product(client)
    first_image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-front.png",
        sort_order=1,
    )
    second_image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=2,
    )

    response = client.get(f"/products/{product['id']}")

    assert response.status_code == 200
    assert response.json() == {
        **product,
        "images": [first_image, second_image],
    }


def test_patch_product_happy_path(client: TestClient) -> None:
    product = create_product(client)

    response = client.patch(
        f"/products/{product['id']}",
        json={
            "stock": 3,
            "energy_rating": "A+",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        **product,
        "stock": 3,
        "energy_rating": "A+",
        "updated_at": response.json()["updated_at"],
    }
    assert response.json()["name"] == product["name"]
    assert response.json()["description"] == product["description"]


def test_delete_product_happy_path(client: TestClient) -> None:
    product = create_product(client)

    response = client.delete(f"/products/{product['id']}")

    assert response.status_code == 200
    assert response.json() == {"id": product["id"]}
    get_response = client.get(f"/products/{product['id']}")
    assert get_response.status_code == 404


def test_delete_product_returns_409_when_product_is_used_in_orders(
    client: TestClient, orders_by_product: dict[int, list[dict]]
) -> None:
    product = create_product(client)
    orders_by_product[product["id"]] = [
        {"id": 1, "status": "created", "created_at": "2026-04-18T00:00:00"}
    ]

    response = client.delete(f"/products/{product['id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": "Product is used in orders"}


def test_delete_product_removes_its_images(client: TestClient) -> None:
    product = create_product(client)
    add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-front.png",
        sort_order=1,
    )
    add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=2,
    )

    response = client.delete(f"/products/{product['id']}")

    assert response.status_code == 200
    assert response.json() == {"id": product["id"]}
    images_response = client.get(f"/products/{product['id']}/images")
    assert images_response.status_code == 404


def test_list_product_images_happy_path(client: TestClient) -> None:
    product = create_product(client)
    second_image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=2,
    )
    first_image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-front.png",
        sort_order=1,
    )

    response = client.get(f"/products/{product['id']}/images")

    assert response.status_code == 200
    assert response.json() == [first_image, second_image]


def test_add_product_image_happy_path(client: TestClient) -> None:
    product = create_product(client)

    image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=0,
    )

    assert image == {
        "id": 1,
        "product_id": product["id"],
        "image_url": "https://example.com/cooler-side.png",
        "sort_order": 0,
        "created_at": image["created_at"],
    }


def test_delete_product_image_happy_path(client: TestClient) -> None:
    product = create_product(client)
    image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=0,
    )

    response = client.delete(f"/products/{product['id']}/images/{image['id']}")

    assert response.status_code == 200
    assert response.json() == {"id": image["id"]}
    list_response = client.get(f"/products/{product['id']}/images")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_product_image_returns_not_found_for_wrong_product(
    client: TestClient,
) -> None:
    first_product = create_product(client)
    second_product = create_product(
        client,
        name="Noctua NH-D15",
        price="199.99",
        stock=3,
        description="Dual tower cooler",
        compatibility="AM5",
        energy_rating="A+",
    )
    image = add_product_image(
        client,
        first_product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=0,
    )

    response = client.delete(f"/products/{second_product['id']}/images/{image['id']}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product image not found"}


def test_create_product_returns_validation_error_for_missing_required_fields(
    client: TestClient,
) -> None:
    response = client.post(
        "/products",
        json={
            "stock": 7,
        },
    )

    assert response.status_code == 422


def test_create_product_returns_validation_error_for_negative_price(
    client: TestClient,
) -> None:
    response = client.post(
        "/products",
        json={
            "name": "Cooler Master 500",
            "price": "-1.00",
            "stock": 7,
            "description": "Tower cooler",
        },
    )

    assert response.status_code == 422


def test_update_product_image_happy_path(client: TestClient) -> None:
    product = create_product(client)
    image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=0,
    )

    response = client.patch(
        f"/products/{product['id']}/images/{image['id']}",
        json={"image_url": "https://example.com/updated.png", "sort_order": 1},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == image["id"]
    assert result["product_id"] == product["id"]
    assert result["image_url"] == "https://example.com/updated.png"
    assert result["sort_order"] == 1


def test_update_product_image_partial(client: TestClient) -> None:
    product = create_product(client)
    image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=0,
    )

    response = client.patch(
        f"/products/{product['id']}/images/{image['id']}",
        json={"sort_order": 2},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["image_url"] == "https://example.com/cooler-side.png"
    assert result["sort_order"] == 2


def test_update_product_image_not_found(client: TestClient) -> None:
    product = create_product(client)

    response = client.patch(
        f"/products/{product['id']}/images/999",
        json={"image_url": "https://example.com/updated.png"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product image not found"}


def test_update_product_image_returns_validation_error_for_negative_sort_order(
    client: TestClient,
) -> None:
    product = create_product(client)
    image = add_product_image(
        client,
        product["id"],
        image_url="https://example.com/cooler-side.png",
        sort_order=0,
    )

    response = client.patch(
        f"/products/{product['id']}/images/{image['id']}",
        json={"sort_order": -1},
    )

    assert response.status_code == 422


def test_add_product_image_returns_validation_error_without_sort_order(
    client: TestClient,
) -> None:
    product = create_product(client)

    response = client.post(
        f"/products/{product['id']}/images",
        json={"image_url": "https://example.com/cooler-side.png"},
    )

    assert response.status_code == 422


def test_list_products_returns_validation_error_for_invalid_limit(
    client: TestClient,
) -> None:
    response = client.get("/products", params={"limit": 0})

    assert response.status_code == 422
