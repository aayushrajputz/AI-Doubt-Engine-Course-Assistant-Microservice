import urllib.request
import time
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def create_doubt():
    print("1. Creating a fresh doubt in PostgreSQL...")
    payload = {
        "title": "How does Redis memory eviction and TTL work?",
        "question": "Can you explain allkeys-lru eviction and TTL expiration in Redis hot-path caching?",
        "course_id": 101,
        "tags": ["redis", "caching", "hot-path"]
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/doubts/",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        doubt_id = res["id"]
        print(f"Created Doubt ID #{doubt_id}: '{res['title']}'\n")
        return doubt_id

def run_stream(round_name, doubt_id):
    print("==================================================")
    print(f"          {round_name}")
    print("==================================================")
    start_time = time.time()
    url = f"{BASE_URL}/doubts/{doubt_id}/stream"
    req = urllib.request.Request(url, method='POST', headers={'Accept': 'text/event-stream'})

    with urllib.request.urlopen(req) as resp:
        first_token_time = None
        for line in resp:
            decoded = line.decode('utf-8', errors='ignore').strip()
            if decoded.startswith('data:'):
                if first_token_time is None:
                    first_token_time = time.time() - start_time
                content = decoded.replace('data:', '').strip()
                if content.startswith('{') and 'usage_metrics' in content:
                    metrics = json.loads(content)
                    total_time = time.time() - start_time
                    print(f"TTFT (Time-to-first-token): {first_token_time*1000:.1f}ms")
                    print(f"Total Response Time: {total_time*1000:.1f}ms")
                    print(f"Cached Response: {metrics.get('cached', False)}")
                    print(f"Total Tokens Used: {metrics['total_tokens']}")
                    print(f"Cost in INR: {metrics['cost_inr']}")
                    print(f"Cost in USD: {metrics['cost_usd']}\n")
                elif content == '[DONE]':
                    break

if __name__ == "__main__":
    # Step 1: Create Doubt
    d_id = create_doubt()

    # Step 2: Round 1 (Cold Call - Cache Miss)
    run_stream("ROUND 1: COLD REQUEST (CACHE MISS)", d_id)

    time.sleep(1)

    # Step 3: Round 2 (Hot Call - Cache Hit)
    run_stream("ROUND 2: SUBSEQUENT REQUEST (CACHE HIT ⚡)", d_id)
