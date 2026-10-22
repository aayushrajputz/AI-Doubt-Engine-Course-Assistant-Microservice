import httpx, asyncio, time, json, sys
sys.stdout.reconfigure(encoding='utf-8')

async def test():
    async with httpx.AsyncClient(timeout=120) as c:
        # Create a similar GIL question with different wording
        r = await c.post("http://127.0.0.1:8000/doubts/", json={
            "title": "GIL threading question",
            "question": "How does GIL in Python impact multithreaded programs?",
            "course_id": 1,
            "tags": ["python"]
        })
        did = r.json()["id"]
        print(f"Created Doubt {did}")

        # Stream and measure time
        start = time.perf_counter()
        lines = []
        async with c.stream("POST", f"http://127.0.0.1:8000/doubts/{did}/stream") as resp:
            async for line in resp.aiter_lines():
                if line:
                    lines.append(line)
        elapsed = time.perf_counter() - start

        print(f"\nResponse time: {elapsed*1000:.0f}ms")
        for l in lines:
            if "CACHE HIT" in l:
                print(l[:120])
            if "usage_metrics" in l:
                print(l)

asyncio.run(test())
