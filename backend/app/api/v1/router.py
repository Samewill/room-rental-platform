from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.areas import router as areas_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.listings import router as listings_router
from app.api.v1.endpoints.users import router as users_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(admin_router)
api_router.include_router(auth_router)
api_router.include_router(areas_router)
api_router.include_router(listings_router)
api_router.include_router(users_router)