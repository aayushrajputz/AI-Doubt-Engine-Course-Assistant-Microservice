import asyncio
import httpx
import sys

async def run_fts_test():
    print("=" * 70)
    print("🧪 TESTING TIER-2 POSTGRES FTS CACHE (Stopwords + Stemming)")
    print("=" * 70)

    transport = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=120.0)
    async with transport as client:
        # Check health first 
        try:
            h = await client.get("/health")
            print(f"✅ Backend Health: {h.status_code}")
        except Exception as e:
            
            print(f"❌ Backend not reachable: {e}")
            return

        # -------------------------------------------------------------
        # STEP 1: Student 1 Asks initial question with filler words
        # -------------------------------------------------------------
        q1 = "I do not understand how reconciliation algorithm works in React"
        print(f"\n1️⃣ [STUDENT 1] Asks Doubt:")
        print(f"   Question: \"{q1}\"")
        print(f"   (Expecting Cold Call -> LLM Inference & DB save)")

        res1 = await client.post("/doubts/", json={
            "user_id": 10,
            "course_id": 101,
            "title": "React reconciliation doubt",
            "question": q1,
            "tags": ["react"]
        })
        d1 = res1.json()
        d1_id = d1["id"]
        print(f"   Created Doubt #{d1_id}. Streaming response...")

        async with client.stream("POST", f"/doubts/{d1_id}/stream") as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                content = line[6:]
                if content.startswith("["):
                    print(f"   Badge: {content}")
                elif "usage_metrics" in content:
                    print(f"   📊 Metrics: {content}")

        # -------------------------------------------------------------
        # STEP 2: Student 2 Asks DIFFERENT words, different stopwords, but same meaning!
        # -------------------------------------------------------------
        # Redis hash will NOT match because strings are different.
        # Postgres FTS english dictionary will strip 'Can', 'you', 'please', 'tell', 'me', 'about'
        # and match stems: 'reconciliation' + 'algorithm' + 'react'!
        q2 = "Can you please tell me about reconciliation algorithms in react? I really need help"
        print(f"\n2️⃣ [STUDENT 2] Asks SAME CORE CONCEPT with different stopwords & phrasing:")
        print(f"   Question: \"{q2}\"")
        print(f"   (Expecting TIER-2: [FTS DICTIONARY CACHE HIT] -> ₹0.00 / 0 Tokens)")

        res2 = await client.post("/doubts/", json={
            "user_id": 11,
            "course_id": 101,
            "title": "Reconciliation doubt 2",
            "question": q2,
            "tags": ["react"]
        })
        d2 = res2.json()
        d2_id = d2["id"]
        print(f"   Created Doubt #{d2_id}. Streaming response...")

        hit_found = False
        async with client.stream("POST", f"/doubts/{d2_id}/stream") as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                content = line[6:]
                if content.startswith("["):
                    print(f"   🎯 BADGE RECEIVED: \033[95m{content}\033[0m")
                    if "FTS DICTIONARY CACHE HIT" in content:
                        hit_found = True
                elif "usage_metrics" in content:
                    print(f"   📊 Metrics: {content}")

        print("\n" + "=" * 70)
        if hit_found:
            print("🏆 RESULT: PASSED! Postgres FTS English dictionary cache hit verified!")
        else:
            print("⚠️ Check stream output above")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_fts_test())
