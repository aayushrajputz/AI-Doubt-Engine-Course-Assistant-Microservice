from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis
from app.core.database import engine
from app.routers.doubt_router import router as doubt_router
from app.models.doubt_model import Base



@asynccontextmanager
async def lifespan(app : FastAPI):
    print("booting backend")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        

    print("DB tabels created")
    

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
    