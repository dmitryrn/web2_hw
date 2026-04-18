from fastapi import FastAPI

from controllers import router

app = FastAPI(title="product-service")
app.include_router(router)
