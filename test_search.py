import asyncio
from app.core.database import async_session
from app.repositories.course_chunk_repository import CourseChunkRepository
from app.services.embedding_service import get_embedding

async def main():
    query = "How to configure ef_construction for vector search?"
    print(f"User Query: '{query}'\n")

    print("Generating query embedding...")
    query_vector = await get_embedding(query)

    repo = CourseChunkRepository()

    async with async_session() as session:
        print("\n=== 1. PURE VECTOR SEARCH (COSINE DISTANCE) ===")
        vector_results = await repo.search_similar_chunks(
            session=session,
            course_id=101,
            query_vector=query_vector,
            limit=2
        )
        for rank, (chunk, sim) in enumerate(vector_results, start=1):
            print(f"[Rank #{rank}] Similarity: {sim:.4f} | Chunk #{chunk.id}: {chunk.content[:60]}...")

        print("\n=== 2. HYBRID SEARCH WITH RRF (VECTOR + KEYWORD) ===")
        rrf_results = await repo.hybrid_search(
            session=session,
            course_id=101,
            query_vector=query_vector,
            query_text=query,
            k=60,
            limit=2
        )
        for rank, (chunk, rrf_score) in enumerate(rrf_results, start=1):
            print(f"[Rank #{rank}] RRF Score: {rrf_score:.6f} | Chunk #{chunk.id}: {chunk.content[:60]}...")

if __name__ == "__main__":
    asyncio.run(main())
