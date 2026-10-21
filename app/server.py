from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis
from app.core.database import engine
from app.routers.doubt_router import router as doubt_router
from app.models.doubt_model import Base
from sqlalchemy import text
from app.models.course_chunk_model import CourseChunk



@asynccontextmanager
async def lifespan(app : FastAPI):
    print("booting backend")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        await conn.run_sync(Base.metadata.create_all) 

        await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_course_chunks_hsnw ON course_chunks USING hnsw (embedding vector_cosine_ops) WITH(m = 16, ef_construction=64)"""))
    print("[psql and pgvcector] tables created successfully")

    
    

    app.state.redis = aioredis.from_url("redis://localhost:6379", decode_responses = True)

    try:
        yield

    finally:
        print("server shutdown")
        await app.state.redis.close()
        await engine.dispose()
        print(" all servers sucessfully shutdown")

app = FastAPI(
    title="AI-ENGINE",
    version="1.0.0",
    description="AI Doubt Engine & Course Assistant microservice",
    lifespan=lifespan
)

app.include_router(doubt_router)

@app.get('/health')
async def health_check():
    return {
        "status" : "healthy",
        "service" : "ai tutor engine",
        "version" : "1.0.0"
    }
    