import httpx
import asyncio

async def test_day_13_video_doubt():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        print("\n" + "="*60)
        print("[TEST] DAY 13: Video Context-Aware Doubt Engine & Cache Test")
        print("="*60)

        # 1. Student A asks question at timestamp = 500s (inside Chapter 2: 451s - 1200s)
        print("\n[STUDENT A] Asking question at 500s (useEffect chapter)...")
        payload_a = {
            "user_id": 99,
            "course_id": 101,
            "video_id": 1,
            "timestamp": 500,
            "title": "Cleanup timing doubt",
            "question": "When does the useEffect cleanup function execute?",
            "tags": ["react", "useeffect"]
        }
        res_a = await client.post("/doubts/", json=payload_a)
        doubt_a_id = res_a.json()["id"]
        print(f"-> Doubt Created: ID={doubt_a_id}, Video={res_a.json()['video_id']}, Timestamp={res_a.json()['timestamp']}s")

        # Stream Student A response
        print("-> Streaming Answer for Student A (Expect LLM Call)...")
        chunks_a = []
        async with client.stream("POST", f"/doubts/{doubt_a_id}/stream") as sr:
            async for line in sr.aiter_lines():
                if line.startswith("data: ") and not "[DONE]" in line:
                    chunks_a.append(line.replace("data: ", ""))
        print(f"-> Student A Response Received ({len(chunks_a)} chunks).")
        first_few_lines = " ".join(chunks_a[:4])
        print(f"   Snippet: {first_few_lines[:150]}...")

        # 2. Student B asks SAME question at timestamp = 550s (Different second, but SAME chapter!)
        print("\n[STUDENT B] Asking SAME question at 550s (different second, same chapter)...")
        payload_b = {
            "user_id": 100,
            "course_id": 101,
            "video_id": 1,
            "timestamp": 550,
            "title": "Cleanup function execution",
            "question": "When does the useEffect cleanup function execute?",
            "tags": ["react", "useeffect"]
        }
        res_b = await client.post("/doubts/", json=payload_b)
        doubt_b_id = res_b.json()["id"]
        print(f"-> Doubt Created: ID={doubt_b_id}, Video={res_b.json()['video_id']}, Timestamp={res_b.json()['timestamp']}s")

        # Stream Student B response -> Must be EXACT CACHE HIT!
        print("-> Streaming Answer for Student B (Expect CACHE HIT)...")
        got_cache_hit = False
        async with client.stream("POST", f"/doubts/{doubt_b_id}/stream") as sr:
            async for line in sr.aiter_lines():
                if "EXACT CACHE HIT" in line:
                    got_cache_hit = True
                    break

        if got_cache_hit:
            print("[SUCCESS] BUCKETED CACHE HIT SUCCESSFUL! (INR 0.00 Cost / 0 LLM Tokens)")
        else:
            print("[FAILURE] Cache hit missed!")

if __name__ == "__main__":
    asyncio.run(test_day_13_video_doubt())
