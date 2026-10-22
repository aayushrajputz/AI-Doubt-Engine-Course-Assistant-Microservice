import asyncio
import httpx
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

async def test_semantic_cache():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("="*60)
        print("STEP 1: Student A asks Question 1 (Cold Call / Cache Miss)")
        print("="*60)
        payload1 = {
            "title": "Python GIL concept",
            "question": "What is Python GIL and how does it affect multi-threading?",
            "course_id": 1,
            "tags": ["python", "threading", "gil"]
        }
        res1 = await client.post(f"{BASE_URL}/doubts/", json=payload1)
        doubt1 = res1.json()
        print(f"Created Doubt 1 ID: {doubt1['id']}")

        print("\nStreaming answer for Doubt 1 from LLM...")
        async with client.stream("POST", f"{BASE_URL}/doubts/{doubt1['id']}/stream") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: {"):
                    metrics = json.loads(line.replace("data: ", ""))
                    print(f"Metrics: {metrics}")
                elif line.startswith("data: "):
                    # Print preview of text
                    chunk = line.replace("data: ", "")
                    if "[DONE]" not in chunk and len(chunk) > 0:
                        print(chunk[:40], end="... ")

        print("\n\n" + "="*60)
        print("STEP 2: Student B asks a Semantically Similar Question")
        print("="*60)
        # Notice: Different words, same meaning!
        payload2 = {
            "title": "Global interpreter lock doubt",
            "question": "Explain global interpreter lock in python and thread performance",
            "course_id": 1,
            "tags": ["python", "concurrency"]
        }
        res2 = await client.post(f"{BASE_URL}/doubts/", json=payload2)
        doubt2 = res2.json()
        print(f"Created Doubt 2 ID: {doubt2['id']}")

        print("\nStreaming answer for Doubt 2 (Expecting SEMANTIC CACHE HIT)...")
        async with client.stream("POST", f"{BASE_URL}/doubts/{doubt2['id']}/stream") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    print(line)

if __name__ == "__main__":
    asyncio.run(test_semantic_cache())
