import httpx
import asyncio
import sys

async def run_interactive_student_demo():
    print("\n" + "="*65)
    print("🎓 LEARNTUBE.AI — LIVE VIDEO DOUBT ASSISTANT DEMO")
    print("="*65)

    base_url = "http://127.0.0.1:8000"

    async with httpx.AsyncClient(base_url=base_url, timeout=40.0) as client:
        # Step 1: List all videos
        print("\n[AVAILABLE VIDEO LECTURES IN SYSTEM]:")
        v_res = await client.get("/admin/videos/course/101")
        videos = v_res.json()
        for v in videos:
            print(f"  -> Video #{v['id']}: '{v['title']}' (Length: {v['duration_seconds']}s)")

        # Scenario: Student asks doubt on Video #1 at 520s
        video_id = 1
        timestamp = 520
        question = "Mujhe samajh nahi aaya ki useEffect me cleanup function return karne se memory leak kaise prevent hota hai?"
        
        print("\n" + "-"*65)
        print(f"🧑‍🎓 [STUDENT DOUBT SUBMISSION]")
        print(f"   Video ID  : #{video_id}")
        print(f"   Timestamp : {timestamp}s (08:40 mins)")
        print(f"   Question  : \"{question}\"")
        print("-"*65)

        # Step 2: Create Doubt
        print("\n-> Submitting doubt to backend...")
        doubt_payload = {
            "user_id": 42,
            "course_id": 101,
            "video_id": video_id,
            "timestamp": timestamp,
            "title": "Cleanup Memory Leak Doubt",
            "question": question,
            "tags": ["react", "useeffect", "memory_leak"]
        }
        res_create = await client.post("/doubts/", json=doubt_payload)
        doubt_data = res_create.json()
        doubt_id = doubt_data["id"]
        print(f"-> Doubt Created Successfully! ID=#{doubt_id}, Status={doubt_data['status']}")

        # Step 3: Stream Live AI Answer
        print("\n" + "="*65)
        print("🤖 [AI DOUBT ENGINE STREAMING RESPONSE]")
        print("="*65 + "\n")

        full_response = []
        metrics_received = None

        async with client.stream("POST", f"/doubts/{doubt_id}/stream") as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                content = line.replace("data: ", "")
                if content == "[DONE]":
                    break
                elif "usage_metrics" in content:
                    metrics_received = content
                elif content.startswith("[EXACT CACHE HIT") or content.startswith("[SEMANTIC CACHE HIT"):
                    print(f"\033[92m{content}\033[0m\n")
                else:
                    # Print streamed token immediately in real-time
                    sys.stdout.write(content)
                    sys.stdout.flush()
                    full_response.append(content)

        # -------------------------------------------------------------
        # STEP 4: STUDENT B — Exact Redis Cache Test (Timestamp Bucketing)
        # -------------------------------------------------------------
        print("\n\n" + "="*65)
        print("🧑‍🎓 [STUDENT B] ASKS SAME QUESTION AT 560s (Different second, same chapter)")
        print("   Expected: [EXACT CACHE HIT] (0 Tokens, ₹0.00 Cost)")
        print("="*65)
        res_b = await client.post("/doubts/", json={
            "user_id": 43,
            "course_id": 101,
            "video_id": 1,
            "timestamp": 560,
            "title": "Cleanup doubt B",
            "question": question, # Exact same question
            "tags": ["react"]
        })
        d_b_id = res_b.json()["id"]

        print(f"-> Streaming Answer for Student B (Doubt #{d_b_id})...\n")
        async with client.stream("POST", f"/doubts/{d_b_id}/stream") as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                content = line.replace("data: ", "")
                if content.startswith("[EXACT CACHE HIT"):
                    print(f"\033[92m>>> {content} <<<\033[0m\n")
                elif "usage_metrics" in content:
                    print(f"📊 [STUDENT B METRICS]: {content}")
                elif content != "[DONE]" and not content.startswith("{"):
                    # Print first 200 chars only
                    sys.stdout.write(content[:80])
                    sys.stdout.flush()

        # -------------------------------------------------------------
        # STEP 5: STUDENT C — Semantic Cache Test (Different Words, Same Meaning)
        # -------------------------------------------------------------
        semantic_question = "How does returning cleanup in useEffect stop memory leaks in React components?"
        print("\n\n" + "="*65)
        print("🧑‍🎓 [STUDENT C] ASKS REPHRASED QUESTION (Different words, same meaning)")
        print(f"   Question: \"{semantic_question}\"")
        print("   Expected: [SEMANTIC CACHE HIT via pgvector HNSW]")
        print("="*65)

        res_c = await client.post("/doubts/", json={
            "user_id": 44,
            "course_id": 101,
            "video_id": 1,
            "timestamp": 510,
            "title": "Semantic cleanup doubt",
            "question": semantic_question, # Rephrased question
            "tags": ["react"]
        })
        d_c_id = res_c.json()["id"]

        print(f"-> Streaming Answer for Student C (Doubt #{d_c_id})...\n")
        async with client.stream("POST", f"/doubts/{d_c_id}/stream") as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                content = line.replace("data: ", "")
                if content.startswith("[SEMANTIC CACHE HIT"):
                    print(f"\033[96m>>> {content} <<<\033[0m\n")
                elif "usage_metrics" in content:
                    print(f"\n📊 [STUDENT C METRICS]: {content}")
                elif content != "[DONE]" and not content.startswith("{"):
                    sys.stdout.write(content)
                    sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(run_interactive_student_demo())
