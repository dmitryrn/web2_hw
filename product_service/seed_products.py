import argparse
import asyncio
import os
from decimal import Decimal

from seed_data import SEED_PRODUCTS


async def seed_products(*, replace: bool, if_empty: bool) -> None:
    os.environ.setdefault("ORDER_SERVICE_URL", "http://localhost:8001")

    from sqlalchemy import delete, func, select

    from db import SessionLocal
    from models import Product, ProductImage

    async with SessionLocal() as session:
        existing_count = await session.scalar(select(func.count()).select_from(Product))
        existing_count = existing_count or 0

        if existing_count > 0 and if_empty and not replace:
            print(f"Skipped seeding: {existing_count} products already exist.")
            return

        if replace:
            await session.execute(delete(ProductImage))
            await session.execute(delete(Product))
            await session.commit()

        products: list[Product] = []
        for item in SEED_PRODUCTS:
            product = Product(
                name=item["name"],
                price=Decimal(item["price"]),
                stock=item["stock"],
                description=item["description"],
                compatibility=item["compatibility"],
                energy_rating=item["energy_rating"],
            )
            session.add(product)
            products.append(product)

        await session.flush()

        for product, item in zip(products, SEED_PRODUCTS, strict=True):
            for sort_order, image_url in enumerate(item["images"]):
                session.add(
                    ProductImage(
                        product_id=product.id,
                        image_url=image_url,
                        sort_order=sort_order,
                    )
                )

        await session.commit()
        print(f"Seeded {len(products)} products.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo products into product-service")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing products and seed fresh demo data",
    )
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Seed only when the products table is empty",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.replace and not args.if_empty:
        args.if_empty = True

    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required to run the seed script")

    asyncio.run(seed_products(replace=args.replace, if_empty=args.if_empty))


if __name__ == "__main__":
    main()
