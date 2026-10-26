import httpx
import asyncio

async def test_video_api():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0) as client:
        # 1. Create Video
        video_payload = {
            "title": "React Hooks Masterclass",
            "url": "https://www.youtube.com/watch?v=dpw9EHDh2bM",
            "course_id": 101,
            "description": "Comprehensive guide to useState, useEffect and custom hooks.",
            "duration_seconds": 1800
        }
        res_v = await client.post("/admin/videos/", json=video_payload)
        print("1. Create Video Status:", res_v.status_code)
        video_data = res_v.json()
        print("   Created Video ID:", video_data.get("id"))
        video_id = video_data["id"]

        # 2. Add Chapter 1: Introduction to useState
        c1_payload = {
            "title": "Introduction to useState",
            "start_time": 0,
            "end_time": 450,
            "summary": "Explains how state is preserved across renders in functional components.",
            "key_concepts": ["useState", "state hook", "immutability"]
        }
        res_c1 = await client.post(f"/admin/videos/{video_id}/chapters", json=c1_payload)
        print("2. Add Chapter 1 Status:", res_c1.status_code, "Title:", res_c1.json().get("title"))

        # 3. Add Chapter 2: useEffect Lifecycle and Cleanup
        c2_payload = {
            "title": "useEffect & Cleanup function",
            "start_time": 451,
            "end_time": 1200,
            "summary": "Deep dive into side effects, API calling, and clearing timers/subscriptions using cleanup return.",
            "key_concepts": ["useEffect", "cleanup function", "dependency array", "memory leak"]
        }
        res_c2 = await client.post(f"/admin/videos/{video_id}/chapters", json=c2_payload)
        print("3. Add Chapter 2 Status:", res_c2.status_code, "Title:", res_c2.json().get("title"))

        # 4. Fetch all chapters for this video
        res_list = await client.get(f"/admin/videos/{video_id}/chapters")
        print("4. Fetch Chapters Status:", res_list.status_code)
        chapters = res_list.json()
        for idx, ch in enumerate(chapters, 1):
            print(f"   [{idx}] {ch['title']} ({ch['start_time']}s - {ch['end_time']}s) - Key Concepts: {ch['key_concepts']}")

if __name__ == "__main__":
    asyncio.run(test_video_api())
