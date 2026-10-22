import httpx, asyncio,json,sys,time

sys.stdout.reconfigure(encoding = "utf-8")

async def chat():
    print("Hey there! Welcome to Doubts AI Chat.")
    print("type `exit` to exit\n")
    course_id = int(input("Please enter your Course Id First : "))

    async with httpx.AsyncClient(timeout=120.0) as client:
        while True:
            question = input("\n You:")
            if question.lower() in ("exit","quit"):
                print("Bye! have a nice day")
                break

            res = await client.post("http://127.0.0.1:8000/doubts/", json={
                "title" : " AI Doubt Engine ",
                "question": question,
                "course_id": course_id,
                "tags": ["general"]
                })
            doubt_id = res.json()["id"]

            async with client.stream("POST", f"http://127.0.0.1:8000/doubts/{doubt_id}/stream") as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if line.startswith("data:"):
                        text = line[6:] if line.startswith("data: ") else line[5:]
                        
                        if text == "[DONE]":
                            print("\n")
                        elif '"event": "usage_metrics"' in text or '"event":"usage_metrics"' in text:
                            try:
                                metrics = json.loads(text)
                                print(f"\n\nTokens: {metrics.get('total_tokens',0)} | Cost: {metrics.get('cost_inr','₹0.00')}")
                            except Exception:
                                pass
                        elif text.startswith("[SEMANTIC CACHE HIT"):
                            print(f"\n {text}\n")
                        else:
                            print(text, end="", flush=True)


asyncio.run(chat())
 
    
      


