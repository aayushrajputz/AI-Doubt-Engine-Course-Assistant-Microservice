import httpx
import asyncio
from app.core.database import async_session
from app.services.embedding_service import get_embedding
from app.models.course_chunk_model import CourseChunk
from sqlalchemy import text

async def seed_chunks_and_test():
    # 1. Database mein do realistic chunks insert karte hain:
    print("[1] Seeding Course Chunks into Postgres...")
    async with async_session() as session:
        # Purane test chunks clear kar lo
        await session.execute(text("DELETE FROM course_chunks WHERE course_id = 101;"))
        await session.commit()

        # Chunk 1: Local Video Chunk (Video 1, at timestamp 520s - exactly inside Chapter 2)
        local_content = "Inside React's useEffect, returning a function creates a cleanup mechanism that cancels timers and unsubscribes event listeners before re-running."
        local_emb = await get_embedding(local_content)
        chunk1 = CourseChunk(
            course_id=101,
            video_id=1,
            timestamp=520,
            content=local_content,
            embedding=local_emb
        )
        session.add(chunk1)

        # Chunk 2: Cross-Video Fallback Chunk (Video 99 - Foundations of JS)
        cross_content = "JavaScript Closures preserve lexical scope variables across renders, which is the foundational engine behind React hook behavior."
        cross_emb = await get_embedding(cross_content)
        chunk2 = CourseChunk(
            course_id=101,
            video_id=99,
            timestamp=120,
            content=cross_content,
            embedding=cross_emb
        )
        session.add(chunk2)
        await session.commit()
        print("    -> 2 Chunks Seeded Successfully!")

    # 2. Test Cases using HTTP Client
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        print("\n" + "="*60)
        print("[TEST 1] Student asks question at 510s (Local Match Expected)")
        print("="*60)
        res1 = await client.post("/doubts/", json={
            "user_id": 1,
            "course_id": 101,
            "video_id": 1,
            "timestamp": 510,
            "title": "Cleanup timer unmount",
            "question": "How does returning a function in useEffect cancel timers and clear event listeners?",
            "tags": ["react", "useeffect"]
        })
        d1_id = res1.json()["id"]
        print(f"Created Doubt #{d1_id} at timestamp 510s")

        print("Streaming Answer for Test 1...")
        async with client.stream("POST", f"/doubts/{d1_id}/stream") as sr:
            async for line in sr.aiter_lines():
                pass # let stream finish
        print("-> Test 1 Stream Completed!")

        print("\n" + "="*60)
        print("[TEST 2] Student asks Cross-Video Topic (RRF Fallback Expected)")
        print("="*60)
        res2 = await client.post("/doubts/", json={
            "user_id": 2,
            "course_id": 101,
            "video_id": 1,
            "timestamp": 510,
            "title": "Lexical Scope and Closures",
            "question": "Explain how JavaScript closures and lexical scope preserve variables across renders.",
            "tags": ["javascript", "closures"]
        })
        d2_id = res2.json()["id"]
        print(f"Created Doubt #{d2_id} on cross-video concept")

        print("Streaming Answer for Test 2...")
        async with client.stream("POST", f"/doubts/{d2_id}/stream") as sr:
            async for line in sr.aiter_lines():
                pass # let stream finish
        print("-> Test 2 Stream Completed!")

if __name__ == "__main__":
    asyncio.run(seed_chunks_and_test())
