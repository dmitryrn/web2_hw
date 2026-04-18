FROM python:3.12-slim

WORKDIR /service

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY product_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY product_service /service
