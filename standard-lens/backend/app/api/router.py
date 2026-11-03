from fastapi import APIRouter

from app.api.routes import admin, ai, health, products, standards, vision

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(admin.router)

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(standards.router)
v1_router.include_router(products.router)
v1_router.include_router(ai.router)
v1_router.include_router(vision.router)
api_router.include_router(v1_router)
