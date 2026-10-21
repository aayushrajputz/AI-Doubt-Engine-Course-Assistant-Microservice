from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/learntube"


engine = create_async_engine(
    DB_URL,
    echo = True,
    
)

async_session = async_sessionmaker(
    bind = engine,
    class_ = AsyncSession,
    expire_on_commit = False
)

async def get_db():
    async with async_session() as session :
        yield session

