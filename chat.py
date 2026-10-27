import httpx, asyncio, json, sys

sys.stdout.reconfigure(encoding="utf-8")

async def chat():
    print("🎓 Hey there! Welcome to LearnTube AI Doubt Engine")
    print("Type `exit` to quit\n")
    
    course_id = int(input(" Enter your Course ID: "))
    
    # Optional video context
    use_video = input("🎬 Kya video lecture ka context dena hai? (y/n): ").strip().lower()
    video_id = None
    timestamp = None
    if use_video == "y":
        video_id = int(input("   Enter Video ID: "))
        timestamp = int(input("   Enter Timestamp (seconds): "))

    async with httpx.AsyncClient(timeout=120.0, base_url="http://127.0.0.1:8000") as client:
        while True:
            question = input("\n You: ")
            if question.lower() in ("exit", "quit"):
                print("Bye! Have a nice day ")
                break

            # Build payload — video_id aur timestamp optional
            payload = {
                "title": "AI Doubt Engine",
                "question": question,
                "course_id": course_id,
                "tags": ["general"]
            }
            if video_id:
                payload["video_id"] = video_id
                payload["timestamp"] = timestamp

            res = await client.post("/doubts/", json=payload)
            doubt_id = res.json()["id"]

            # Stream the answer
            async with client.stream("POST", f"/doubts/{doubt_id}/stream") as response:
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    text = line[6:] if line.startswith("data: ") else line[5:]

                    if text == "[DONE]":
                        print("\n")
                    elif text.startswith("[EXACT CACHE HIT"):
                        print(f"\n {text}")
                    elif text.startswith("[SEMANTIC CACHE HIT"):
                        print(f"\n {text}")
                    elif '"event": "usage_metrics"' in text or '"event":"usage_metrics"' in text:
                        try:
                            metrics = json.loads(text)
                            print(f"\n Tokens: {metrics.get('total_tokens',0)} | Cost: {metrics.get('cost_inr','₹0.00')}")
                        except Exception:
                            pass
                    else:
                        print(text, end="", flush=True)

asyncio.run(chat())
