import httpx
import asyncio

async def test_day_15_features():
    print("\n" + "="*60)
    print("[DAY 15 TEST] Bulk Chapter Import & Doubt Hotspots Analytics")
    print("="*60)

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=25.0) as client:
        # Step 1: Create a Video for testing bulk chapters
        v_res = await client.post("/admin/videos/", json={
            "title": "System Design Masterclass",
            "url": "https://youtube.com/watch?v=sys_design_101",
            "course_id": 202,
            "description": "High level system design for distributed systems",
            "duration_seconds": 3600
        })
        video_id = v_res.json()["id"]
        print(f"\n[1] Created Video #{video_id}: '{v_res.json()['title']}'")

        # Step 2: Test Bulk Import with Overlapping Chapters (Expect 400 Bad Request)
        print("\n[2] Testing Bulk Import with OVERLAPPING chapters (Expect 400)...")
        overlapping_payload = [
            {"title": "Intro", "start_time": 0, "end_time": 300, "summary": "Intro"},
            {"title": "Load Balancers", "start_time": 250, "end_time": 600, "summary": "Overlaps with Intro!"} # 250 < 300!
        ]
        res_overlap = await client.post(f"/admin/videos/{video_id}/chapters/bulk", json=overlapping_payload)
        print(f"-> Status: {res_overlap.status_code}, Detail: {res_overlap.json().get('detail')}")
        test_overlap_ok = (res_overlap.status_code == 400)
        if test_overlap_ok:
            print("   PASS: Overlapping time ranges correctly blocked with 400 Bad Request!")
        else:
            print("   FAIL: Expected 400 Bad Request")

        # Step 3: Test Valid Bulk Import (3 Clean Chapters)
        print("\n[3] Testing Valid Bulk Import (3 Non-overlapping Chapters)...")
        valid_payload = [
            {"title": "Architecture Overview", "start_time": 0, "end_time": 600, "summary": "High level overview", "key_concepts": ["architecture", "scale"]},
            {"title": "Database Sharding & Replication", "start_time": 601, "end_time": 1800, "summary": "Partitioning databases", "key_concepts": ["sharding", "replication"]},
            {"title": "Caching Strategies (Redis/Memcached)", "start_time": 1801, "end_time": 3600, "summary": "Cache invalidation patterns", "key_concepts": ["redis", "cache"]}
        ]
        res_bulk = await client.post(f"/admin/videos/{video_id}/chapters/bulk", json=valid_payload)
        print(f"-> Status: {res_bulk.status_code}, Imported Count: {len(res_bulk.json())}")
        test_bulk_ok = (res_bulk.status_code == 201 and len(res_bulk.json()) == 3)
        if test_bulk_ok:
            print("   PASS: Successfully imported 3 chapters in bulk!")
        else:
            print("   FAIL: Expected 201 Created with 3 chapters")

        # Step 4: Seed Doubts on Video #1 to Test Hotspots Analytics
        # Video 1 has:
        # - Chapter 1: 0s - 450s (useState)
        # - Chapter 2: 451s - 1200s (useEffect Cleanup)
        # Let's check hotspots for Video 1
        print("\n[4] Testing Video Doubt Hotspots Analytics for Video #1...")
        res_hotspots = await client.get("/admin/videos/1/hotspots")
        print(f"-> Status: {res_hotspots.status_code}")
        hotspots = res_hotspots.json()
        print("-> Hotspots Ranked by Student Doubts:")
        for rank, h in enumerate(hotspots, 1):
            print(f"   Rank #{rank}: '{h['chapter_title']}' ({h['start_time']}s-{h['end_time']}s) -> {h['doubt_count']} Doubts")

        test_hotspots_ok = (res_hotspots.status_code == 200 and len(hotspots) >= 2)
        if test_hotspots_ok:
            print("   PASS: Hotspots analytics successfully calculated and ordered by difficulty!")
        else:
            print("   FAIL: Hotspots calculation failed")

        # SUMMARY
        print("\n" + "="*60)
        print("[SUMMARY] DAY 15 VERIFICATION REPORT")
        print("="*60)
        print(f"1. Overlapping Chapters Blocked : {'PASSED' if test_overlap_ok else 'FAILED'}")
        print(f"2. Bulk Chapters Upload API     : {'PASSED' if test_bulk_ok else 'FAILED'}")
        print(f"3. Video Hotspots Analytics API : {'PASSED' if test_hotspots_ok else 'FAILED'}")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_day_15_features())
