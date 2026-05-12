import argparse
import asyncio
import os
from decimal import Decimal
from random import Random

from seed_data import SEED_PRODUCTS


def generate_seed_products(count: int = 100) -> list[dict[str, object]]:
    rng = Random(20260507)

    product_types = [
        {
            "name": "Светодиодная лампа",
            "category": "headlight",
            "compatibility": ["H1", "H4", "H7", "H11", "HB3", "HB4", None],
            "energy_rating": ["A", "A+", "A++", None],
            "descriptions": [
                "Яркая лампа для ближнего и дальнего света с быстрым запуском.",
                "Стабильное освещение дороги с хорошей цветовой температурой.",
                "Подходит для повседневной езды и поездок в плохую погоду.",
            ],
        },
        {
            "name": "Галогенная лампа",
            "category": "headlight",
            "compatibility": ["H4", "H7", "H11", "9005", "9006", "12V", None],
            "energy_rating": ["B", "A", None],
            "descriptions": [
                "Классическая лампа для штатной оптики с ровным световым пучком.",
                "Надежный вариант для замены изношенной заводской лампы.",
                "Оптимальный баланс ресурса, яркости и стоимости.",
            ],
        },
        {
            "name": "Комплект салонных ламп",
            "category": "interior",
            "compatibility": ["T10", "C5W", "Festoon 36mm", "Универсальная", None],
            "energy_rating": ["A", "A+", None],
            "descriptions": [
                "Комплект для мягкой и равномерной подсветки салона.",
                "Помогает обновить интерьер и улучшить видимость в салоне.",
                "Подходит для плафонов салона, багажника и подсветки дверей.",
            ],
        },
        {
            "name": "Противотуманная лампа",
            "category": "fog",
            "compatibility": ["H8", "H10", "H11", "PSX24W", "Универсальная", None],
            "energy_rating": ["A", "B", None],
            "descriptions": [
                "Создает плотный световой поток для тумана и мокрой дороги.",
                "Улучшает заметность автомобиля и обзор в сложных условиях.",
                "Подходит для замены штатных ламп в ПТФ без сложной установки.",
            ],
        },
        {
            "name": "Лампа заднего хода",
            "category": "rear",
            "compatibility": ["P21W", "W16W", "T15", "Универсальная", None],
            "energy_rating": ["A", "A+", None],
            "descriptions": [
                "Повышает яркость при движении задним ходом в темное время суток.",
                "Делает маневры на парковке заметно безопаснее и удобнее.",
                "Хорошо подходит для городских автомобилей и кроссоверов.",
            ],
        },
        {
            "name": "Лампа подсветки номера",
            "category": "plate",
            "compatibility": ["C5W", "T10", "SV8.5", "Универсальная", None],
            "energy_rating": ["A", None],
            "descriptions": [
                "Компактная лампа для чистой и яркой подсветки номерного знака.",
                "Обеспечивает аккуратный внешний вид и стабильную работу.",
                "Подходит для замены тусклой штатной подсветки без доработок.",
            ],
        },
    ]

    feature_phrases = [
        "Корпус устойчив к вибрациям.",
        "Холодный белый оттенок света.",
        "Теплый свет без лишней синевы.",
        "Подходит для длительных поездок.",
        "Быстро выходит на рабочую яркость.",
        "Удобна для сезонной замены.",
        "Хорошо работает в городском цикле.",
        "Не требует сложного обслуживания.",
    ]

    image_topics = {
        "headlight": "car-headlight-bulb",
        "interior": "car-interior-light",
        "fog": "fog-lamp-car",
        "rear": "reverse-light-car",
        "plate": "license-plate-light-car",
    }

    products: list[dict[str, object]] = []

    for index in range(count):
        product_type = product_types[index % len(product_types)]
        temperature = rng.choice(["3000K", "4300K", "5000K", "6000K", "6500K"])
        wattage = rng.choice(["5W", "8W", "12W", "18W", "21W", "35W", "55W"])
        name = f"{product_type['name']} {temperature} {wattage} #{index + 1}"

        description_parts = [
            rng.choice(product_type["descriptions"]),
            rng.choice(feature_phrases),
        ]
        if rng.random() < 0.6:
            description_parts.append(f"Цветовая температура: {temperature}.")
        if rng.random() < 0.5:
            description_parts.append(f"Номинальная мощность: {wattage}.")

        image_count = rng.randint(0, 3)
        topic = image_topics[product_type["category"]]
        images = [
            f"https://picsum.photos/seed/{topic}-{index + 1}-{image_index + 1}/1200/900"
            for image_index in range(image_count)
        ]

        products.append(
            {
                "name": name,
                "price": f"{rng.randint(20, 199) + rng.choice([0, 49, 99]) / 100:.2f}",
                "stock": rng.randint(0, 5000),
                "description": " ".join(description_parts),
                "compatibility": rng.choice(product_type["compatibility"]),
                "energy_rating": rng.choice(product_type["energy_rating"]),
                "images": images,
            }
        )

    return products


async def seed_products(*, replace: bool, if_empty: bool) -> None:
    os.environ.setdefault("ORDER_SERVICE_URL", "http://localhost:8001")
    os.environ.setdefault("JWT_SECRET", "development-admin-jwt-secret-32-bytes")

    from sqlalchemy import delete, func, select

    from db import SessionLocal
    from models import Product, ProductImage

    seed_items = [*SEED_PRODUCTS, *generate_seed_products(100)]

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
        for item in seed_items:
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

        for product, item in zip(products, seed_items, strict=True):
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
