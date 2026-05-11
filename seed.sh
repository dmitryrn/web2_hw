#!/usr/bin/env sh
set -eu

DATABASE_URL=postgresql+asyncpg://products:products@localhost:5433/products \
./.venv_user/bin/python product_service/seed_products.py --replace

DATABASE_URL=postgresql+asyncpg://admins:admins@localhost:5435/admins \
./.venv_user/bin/python admin_service/seed.py --if-empty
