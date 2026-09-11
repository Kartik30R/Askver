from fastapi import APIRouter

from app.api.v1.controllers.auth_controller import router as auth_router
from app.api.v1.controllers.knowledge_base_controller import router as knowledge_base_router
from app.api.v1.controllers.documents_controller import router as documents_router
from app.api.v1.controllers.deal_controller import router as deal_router
from app.api.v1.controllers.pipeline_controller import router as pipeline_router
from app.api.v1.controllers.reports_controller import router as reports_router
from app.api.v1.controllers.chat_controller import router as chat_router

api_router = APIRouter()

# Register all API endpoints
api_router.include_router(auth_router)
api_router.include_router(knowledge_base_router)
api_router.include_router(deal_router)
api_router.include_router(documents_router)
api_router.include_router(pipeline_router)
api_router.include_router(reports_router)
api_router.include_router(chat_router)