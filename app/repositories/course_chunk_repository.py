from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models.course_chunk_model import CourseChunk
from app.models.doubt_model import Doubt
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

    async def search_bounded_chunks(
        self,
        session: AsyncSession,
        video_id: int,
        start_time: int,
        end_time: int,
        query_vector: list[float],
        limit: int = 3
    ) -> list[tuple[CourseChunk, float]]:
        stmt = (
            select(
                CourseChunk,
                (1 - CourseChunk.embedding.cosine_distance(query_vector)).label("similarity")
            )
            .where(CourseChunk.video_id == video_id)
            .where(CourseChunk.timestamp >= start_time)
            .where(CourseChunk.timestamp <= end_time)
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
    
    
    async def find_semantically_similar_doubts(self,session, course_id, query_vector, threshold=0.75,limit=1):        
        stmt = (
            select(Doubt, (1- Doubt.embedding.cosine_distance(query_vector)).label("similarity"))
            .where(Doubt.course_id == course_id)
            .where(Doubt.ai_answer.isnot(None))
            .order_by(Doubt.embedding.cosine_distance(query_vector)).limit(limit)
        )
        result = await session.execute(stmt)
        row = result.first()
        if row :
            doubt_obj, similarity = row[0],row[1]
            if similarity>= threshold:
                return doubt_obj, similarity
        return None 
    
    async def find_fts_similar_doubt(
        self,
        session: AsyncSession,
        course_id: int,
        question_text: str,
        video_id: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None
    ) -> Doubt | None:
        """
        Postgres Full-Text Search (english dictionary):
        Strips stopwords & conversational filler, matches root lexemes using ts_rank.
        """
        # Exclude common conversational noise lexemes from search tokens
        sql = """
        WITH query_lexemes AS (
            SELECT string_agg(lexeme, ' | ') as ts_q
            FROM unnest(to_tsvector('english', :input)) as lexeme
            WHERE lexeme NOT IN ('tell', 'need', 'help', 'pleas', 'realli', 'know', 'want', 'explain', 'can', 'sir')
        )
        SELECT d.id, ts_rank(to_tsvector('english', d.question), to_tsquery('english', q.ts_q)) as score
        FROM doubts d, query_lexemes q
        WHERE d.course_id = :course_id
          AND d.ai_answer IS NOT NULL
          AND q.ts_q IS NOT NULL
          AND to_tsvector('english', d.question) @@ to_tsquery('english', q.ts_q)
          AND (CAST(:video_id AS INTEGER) IS NULL OR d.video_id = CAST(:video_id AS INTEGER))
          AND (CAST(:start_time AS INTEGER) IS NULL OR d.timestamp >= CAST(:start_time AS INTEGER))
          AND (CAST(:end_time AS INTEGER) IS NULL OR d.timestamp <= CAST(:end_time AS INTEGER))
        ORDER BY score DESC
        LIMIT 1;
        """
        params = {
            "input": question_text,
            "course_id": course_id,
            "video_id": video_id,
            "start_time": start_time,
            "end_time": end_time
        }
        res = await session.execute(text(sql), params)
        row = res.first()
        if row and row[1] and row[1] >= 0.01:
            doubt_id = row[0]
            stmt = select(Doubt).where(Doubt.id == doubt_id)
            d_res = await session.execute(stmt)
            return d_res.scalar_one_or_none()
        return None
       

       