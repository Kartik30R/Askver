from fastapi import APIRouter

from app.api.v1.controllers.auth_controller import router as auth_router

api_router = APIRouter()

# Register Auth Endpoints
api_router.include_router(auth_router)

# Future endpoints can be attached here as the app grows:
# api_router.include_router(documents_router)
# api_router.include_router(analysis_router)