# Lightbulb online store
## Starting
```
docker compose up
```

## Running tests

### Product service
```
cd product_service
python -m pytest tests/ -v
```

### Order service
```
cd order_service
python -m pytest tests/ -v
```

### Admin service
```
cd admin_service
JWT_SECRET=test-secret-with-at-least-32-bytes python -m pytest tests/ -v
```
