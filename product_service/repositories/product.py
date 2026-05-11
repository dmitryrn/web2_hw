from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Product, ProductImage
from schemas import ProductCreate, ProductImageCreate, ProductImageUpdate, ProductUpdate


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self) -> Select[tuple[Product]]:
        return (
            select(Product).options(selectinload(Product.images)).order_by(Product.id)
        )

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
        query = self._base_query()

        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))
        if compatibility:
            query = query.where(Product.compatibility == compatibility)
        if energy_rating:
            query = query.where(Product.energy_rating == energy_rating)
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if in_stock is True:
            query = query.where(Product.stock > 0)

        result = await self._session.scalars(query.limit(limit).offset(offset))
        return list(result)

    async def get(self, id: int) -> Product | None:
        return await self._session.scalar(self._base_query().where(Product.id == id))

    async def lookup(self, ids: set[int]) -> list[Product]:
        result = await self._session.scalars(
            select(Product)
            .options(selectinload(Product.images))
            .where(Product.id.in_(ids))
            .order_by(Product.id)
        )
        return list(result)

    async def create(self, data: ProductCreate) -> Product:
        product = Product(**data.model_dump())
        self._session.add(product)
        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def update(self, id: int, data: ProductUpdate) -> Product | None:
        product = await self._session.get(Product, id)
        if product is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await self._session.commit()
        await self._session.refresh(product)
        return await self.get(id)

    async def delete(self, id: int) -> bool:
        result = await self._session.execute(delete(Product).where(Product.id == id))
        if result.rowcount == 0:
            return False
        await self._session.commit()
        return True


class ProductImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_product(self, product_id: int) -> list[ProductImage]:
        result = await self._session.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order)
        )
        return list(result)

    async def create(self, product_id: int, data: ProductImageCreate) -> ProductImage:
        image = ProductImage(product_id=product_id, **data.model_dump())
        self._session.add(image)
        await self._session.commit()
        await self._session.refresh(image)
        return image

    async def update(
        self, product_id: int, image_id: int, data: ProductImageUpdate
    ) -> ProductImage | None:
        image = await self._session.scalar(
            select(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
            )
        )
        if image is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(image, field, value)

        await self._session.commit()
        await self._session.refresh(image)
        return image

    async def delete(self, product_id: int, image_id: int) -> bool:
        result = await self._session.execute(
            delete(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
            )
        )
        if result.rowcount == 0:
            return False
        await self._session.commit()
        return True
