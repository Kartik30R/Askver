# from contextlib import asynccontextmanager

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# from agents.graph import configure_deal_intelligence_graph
# from app.api.v1.router import api_router
# from app.core.config import settings
# from app.core.database import Base, engine
# from app.db.models.execution_history import ExecutionHistory  # Register model with Base


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

#     async with AsyncPostgresSaver.from_conn_string(settings.CHECKPOINT_DATABASE_URL) as checkpointer:
#         await checkpointer.setup()
#         configure_deal_intelligence_graph(checkpointer)
#         yield

#     graph = getattr(app.state, "deal_graph", None)
#     if graph is not None:
#         app.state.deal_graph = None


# app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# # CORS middleware for React frontend communication
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",],  # Vite default frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Register V1 API Router
# app.include_router(api_router, prefix=settings.API_V1_STR)


# @app.get("/")
# async def root():
#     return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import text

from agents.graph import configure_deal_intelligence_graph
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
import app.db.models  # noqa: F401  # register all ORM models before create_all


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # 1. Ensure vector extension exists via run_sync
        await conn.run_sync(
            lambda sync_conn: sync_conn.execute(
                text("CREATE EXTENSION IF NOT EXISTS vector")
            )
        )
        # 2. Create tables
        await conn.run_sync(Base.metadata.create_all)

    checkpoint_url = settings.CHECKPOINT_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        await checkpointer.setup()
        configure_deal_intelligence_graph(checkpointer)
        yield

    graph = getattr(app.state, "deal_graph", None)
    if graph is not None:
        app.state.deal_graph = None


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS middleware for React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],  # Vite default frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register V1 API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}