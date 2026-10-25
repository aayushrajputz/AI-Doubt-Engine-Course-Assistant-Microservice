from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis
from app.core.database import engine
from app.routers.doubt_router import router as doubt_router
from app.models.doubt_model import Base
from sqlalchemy import text
from app.models.course_chunk_model import CourseChunk
from fastapi import Response, status
import time
import uuid
from fastapi import Request
from app.core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Booting AI Doubt Engine & Microservice...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_course_chunks_hsnw ON course_chunks USING hnsw (embedding vector_cosine_ops) WITH(m = 16, ef_construction=64)"""))
    logger.info("PostgreSQL tables and pgvector HNSW index initialized")

    app.state.redis = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    logger.info("Connected to Redis 7")

    try:
        yield
    finally:
        logger.info("Graceful shutdown initiated...")
        await app.state.redis.close()
        await engine.dispose()
        logger.info("All database and Redis connections successfully closed")

app = FastAPI(
    title="AI-ENGINE",
    version="1.0.0",
    description="AI Doubt Engine & Course Assistant microservice",
    lifespan=lifespan
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    logger.info(f"[{request_id}] START {request.method} {request.url.path}")

    response = await call_next(request)

    latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"[{request_id}] DONE  {request.method} {request.url.path} - {response.status_code} in {latency_ms}ms")

    response.headers["X-Request-ID"] = request_id
    return response

app.include_router(doubt_router)

@app.get('/health')
async def health_check(response: Response):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    try:
        await app.state.redis.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    is_healthy = (db_status == "healthy" and redis_status == "healthy")
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "ai-doubt-engine",
        "version": "1.0.0",
        "dependencies": {
            "postgres": db_status,
            "redis": redis_status
        }
    }

    