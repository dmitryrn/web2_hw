import httpx

from models import Product, ProductImage
from repositories import ProductImageRepository, ProductRepository
from schemas import (
    ProductCreate,
    ProductImageCreate,
    ProductImageUpdate,
    ProductUpdate,
)
from services.exceptions import (
    ProductInUseError,
    ProductNotFoundError,
    ServiceUnavailableError,
)
from settings import settings


class ProductService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self._repo = product_repo

    async def get_all(
        self,
        *,
        search: str | None = None,
        compatibility: str | None = None,
        energy_rating: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        in_stock: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        return await self._repo.get_all(
            search=search,
            compatibility=compatibility,
            energy_rating=energy_rating,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            limit=limit,
            offset=offset,
        )

    async def get(self, id: int) -> Product | None:
        return await self._repo.get(id)

    async def lookup(self, ids: set[int]) -> list[Product]:
        return await self._repo.lookup(ids)

    async def create(self, data: ProductCreate) -> Product:
        return await self._repo.create(data)

    async def update(self, id: int, data: ProductUpdate) -> Product | None:
        return await self._repo.update(id, data)

    async def delete(self, id: int) -> bool:
        if await self._has_orders(id):
            raise ProductInUseError("Product is used in orders")
        return await self._repo.delete(id)

    async def _has_orders(self, product_id: int) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(
                    f"{settings.order_service_url}/orders/by-product/{product_id}"
                )
            except httpx.HTTPError:
                raise ServiceUnavailableError("Order service unavailable")

        if response.status_code != 200:
            raise ServiceUnavailableError("Order service unavailable")

        return bool(response.json())


class ProductImageService:
    def __init__(
        self,
        product_repo: ProductRepository,
        image_repo: ProductImageRepository,
    ) -> None:
        self._product_repo = product_repo
        self._image_repo = image_repo

    async def _ensure_product_exists(self, product_id: int) -> None:
        if await self._product_repo.get(product_id) is None:
            raise ProductNotFoundError("Product not found")

    async def list(self, product_id: int) -> list[ProductImage]:
        await self._ensure_product_exists(product_id)
        return await self._image_repo.list_by_product(product_id)

    async def create(self, product_id: int, data: ProductImageCreate) -> ProductImage:
        await self._ensure_product_exists(product_id)
        return await self._image_repo.create(product_id, data)

    async def update(
        self, product_id: int, image_id: int, data: ProductImageUpdate
    ) -> Product | None:
        return await self._image_repo.update(product_id, image_id, data)

    async def delete(self, product_id: int, image_id: int) -> bool:
        return await self._image_repo.delete(product_id, image_id)
