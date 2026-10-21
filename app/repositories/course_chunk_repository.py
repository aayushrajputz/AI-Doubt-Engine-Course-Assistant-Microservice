from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.course_chunk_model import CourseChunk

class CourseChunkRepository:
    async def create_chunk(
        self,
        session: AsyncSession,
        course_id: int,
        content: str,
        embedding: list[float]
    ) -> CourseChunk:
        chunk = CourseChunk(
            course_id=course_id,
            content=content,
            embedding=embedding
        )
        session.add(chunk)
        await session.commit()
        await session.refresh(chunk)
        return chunk

    async def search_similar_chunks(
        self,
        session: AsyncSession,
        course_id: int,
        query_vector: list[float],
        limit: int = 3
    ) -> list[tuple[CourseChunk, float]]:
        stmt = (
            select(
                CourseChunk,
                (1 - CourseChunk.embedding.cosine_distance(query_vector)).label("similarity")
            )
            .where(CourseChunk.course_id == course_id)
            .order_by(CourseChunk.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.all())


    async def hybrid_search(
        self,
        session: AsyncSession,
        course_id: int,
        query_vector: list[float],
        query_text: str,
        k: int = 60,
        limit: int = 3
    ) -> list[tuple[CourseChunk, float]]:
        vector_stmt = (
            select(CourseChunk).where(CourseChunk.course_id == course_id)
            .order_by(CourseChunk.embedding.cosine_distance(query_vector)).limit(5)
        )
        vector_res = await session.execute(vector_stmt)
        vector_chunks = list(vector_res.scalars().all())

        keywords = [w.strip() for w in query_text.split() if len(w.strip()) > 3]
        keyword_filter = CourseChunk.content.ilike(f"%{keywords[0]}%") if keywords else True

        keyword_stmt = (
            select(CourseChunk)
            .where(CourseChunk.course_id == course_id)
            .where(keyword_filter)
            .limit(5)
        )

        keyword_res = await session.execute(keyword_stmt)
        keyword_chunks = list(keyword_res.scalars().all())
        
        rrf_scores = {}
        chunks_map = {}

        for rank, chunk in enumerate(vector_chunks, start=1):
            chunks_map[chunk.id] = chunk
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + 1.0 / (k + rank)

        for rank, chunk in enumerate(keyword_chunks, start=1):
            chunks_map[chunk.id] = chunk
            rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + 1.0 / (k + rank)

        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        return [(chunks_map[cid], rrf_scores[cid]) for cid in sorted_chunk_ids[:limit]]
    
    
    