from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Product, ProductImage
from repositories import ProductImageRepository, ProductRepository
from schemas import (
    ProductCreate,
    ProductImageCreate,
    ProductImageRead,
    ProductImageUpdate,
    ProductLookupRead,
    ProductLookupRequest,
    ProductRead,
    ProductUpdate,
)
from security import require_jwt
from services import ProductImageService, ProductService
from services.exceptions import (
    ProductInUseError,
    ProductNotFoundError,
    ServiceUnavailableError,
)


router = APIRouter()


def get_product_service(session: AsyncSession = Depends(get_session)) -> ProductService:
    return ProductService(ProductRepository(session))


def get_image_service(
    session: AsyncSession = Depends(get_session),
) -> ProductImageService:
    return ProductImageService(
        ProductRepository(session), ProductImageRepository(session)
    )


@router.get("/products", response_model=list[ProductRead])
async def list_products(
    search: str | None = None,
    compatibility: str | None = None,
    energy_rating: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    in_stock: bool | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ProductService = Depends(get_product_service),
) -> list[Product]:
    return await service.get_all(
        search=search,
        compatibility=compatibility,
        energy_rating=energy_rating,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{id}", response_model=ProductRead)
async def get_product(
    id: int, service: ProductService = Depends(get_product_service)
) -> Product:
    product = await service.get(id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.post(
    "/products/lookup",
    response_model=list[ProductLookupRead],
    dependencies=[Depends(require_jwt)],
)
async def lookup_products(
    payload: ProductLookupRequest,
    service: ProductService = Depends(get_product_service),
) -> list[Product]:
    return await service.lookup(set(payload.ids))


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_jwt)],
)
async def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> Product:
    product = await service.create(payload)
    return await service.get(product.id)


@router.patch(
    "/products/{id}", response_model=ProductRead, dependencies=[Depends(require_jwt)]
)
async def patch_product(
    id: int,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> Product:
    product = await service.update(id, payload)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.delete("/products/{id}", dependencies=[Depends(require_jwt)])
async def delete_product(
    id: int,
    service: ProductService = Depends(get_product_service),
) -> dict[str, int]:
    try:
        deleted = await service.delete(id)
    except ProductInUseError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is used in orders",
        )
    except ServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable",
        )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return {"id": id}


@router.get(
    "/products/{id}/images",
    response_model=list[ProductImageRead],
    dependencies=[Depends(require_jwt)],
)
async def list_product_images(
    id: int,
    service: ProductImageService = Depends(get_image_service),
) -> list[ProductImage]:
    try:
        return await service.list(id)
    except ProductNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )


@router.post(
    "/products/{id}/images",
    response_model=ProductImageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_jwt)],
)
async def add_product_image(
    id: int,
    payload: ProductImageCreate,
    service: ProductImageService = Depends(get_image_service),
) -> ProductImage:
    try:
        return await service.create(id, payload)
    except ProductNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )


@router.patch(
    "/products/{id}/images/{imageId}",
    response_model=ProductImageRead,
    dependencies=[Depends(require_jwt)],
)
async def update_product_image(
    id: int,
    imageId: int,
    payload: ProductImageUpdate,
    service: ProductImageService = Depends(get_image_service),
) -> ProductImage:
    image = await service.update(id, imageId, payload)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product image not found"
        )
    return image


@router.delete(
    "/products/{id}/images/{imageId}", dependencies=[Depends(require_jwt)]
)
async def delete_product_image(
    id: int,
    imageId: int,
    service: ProductImageService = Depends(get_image_service),
) -> dict[str, int]:
    deleted = await service.delete(id, imageId)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product image not found"
        )
    return {"id": imageId}
