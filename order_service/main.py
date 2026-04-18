from fastapi import FastAPI

from controllers.order_controller import router as order_router

app = FastAPI(title="order-service")
app.include_router(order_router)
