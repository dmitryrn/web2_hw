from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers.order_controller import router as order_router

app = FastAPI(title="order-service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(order_router)
