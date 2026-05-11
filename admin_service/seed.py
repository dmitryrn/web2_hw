import argparse
import asyncio
import os


async def seed_admin(*, if_empty: bool) -> None:
    from sqlalchemy import func, select

    from db import Database
    from models import AdminUser
    from repositories import AdminRepository
    from security import hash_password

    database = Database.from_url(os.environ["DATABASE_URL"])

    try:
        async with database.session_factory() as session:
            existing_count = await session.scalar(
                select(func.count()).select_from(AdminUser)
            )
            existing_count = existing_count or 0

            if existing_count > 0 and if_empty:
                print(f"Skipped seeding: {existing_count} admin users already exist.")
                return

            repo = AdminRepository(session)
            if await repo.get_by_username("admin") is not None:
                print("Skipped seeding: admin user already exists.")
                return

            await repo.create(username="admin", password_hash=hash_password("admin"))
            print("Seeded admin user.")
    finally:
        await database.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed default admin user")
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Seed only when no admin users exist",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.if_empty:
        args.if_empty = True

    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required to run the seed script")

    asyncio.run(seed_admin(if_empty=args.if_empty))


if __name__ == "__main__":
    main()
