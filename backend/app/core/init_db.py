# """
# Database initialization - Create PostgreSQL checkpointing and execution history tables.
# Run this once to set up required tables for LangGraph PostgreSQL checkpointer.
# """
# import asyncio
# from sqlalchemy.ext.asyncio import create_async_engine
# from sqlalchemy.orm import DeclarativeBase

# from app.core.config import settings
# from app.db.models.execution_history import ExecutionHistory
# from app.core.database import Base


# async def init_db():
#     """Create all tables including LangGraph checkpointing tables."""
#     engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
#     async with engine.begin() as conn:
#         # Create execution history table
#         await conn.run_sync(Base.metadata.create_all)
        
#         # LangGraph PostgreSQL checkpointer will auto-create langgraph_checkpoints table
#         print("✓ Created execution_history table")
#         print("✓ Database initialized")
    
#     await engine.dispose()


# if __name__ == "__main__":
#     asyncio.run(init_db())
"""
Database initialization - Create PostgreSQL checkpointing and execution history tables.
Run this once to set up required tables for LangGraph PostgreSQL checkpointer.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
import app.db.models  # noqa: F401


async def init_db():
    """Create all tables including app ORM tables and required PostgreSQL extensions."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: sync_conn.execute(
                text("CREATE EXTENSION IF NOT EXISTS vector")
            )
        )
        await conn.run_sync(Base.metadata.create_all)

    from app.core.database import ensure_meeting_schema_compatibility
    await ensure_meeting_schema_compatibility()

    print("✓ Created vector extension and database tables")
    print("✓ Database initialized")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())