from fastapi import HTTPException, status
from redis.asyncio import Redis

MAX_REQ_PER_HOUR = 5
MAX_TOKENS_PER_HOUR = 10000
WINDOW_SECONDS = 3600

async def check_rate_limit(redis: Redis, user_id: int) -> dict:
    req_key = f"rate_limit:user:{user_id}:requests"
    token_key = f"rate_limit:user:{user_id}:tokens"

    # 1. Pehle token check karo (sirf read)
    current_tokens = int(await redis.get(token_key) or 0)
    if current_tokens >= MAX_TOKENS_PER_HOUR:
        token_ttl = await redis.ttl(token_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Hourly token budget exceeded. Please try again later.",
                "retry_after_seconds": max(0, token_ttl)
            }
        )

    # 2. Ab request count increment karo
    current_reqs = await redis.incr(req_key)
    if current_reqs == 1:
        await redis.expire(req_key, WINDOW_SECONDS)

    req_ttl = await redis.ttl(req_key)

    if current_reqs > MAX_REQ_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Hourly request limit exceeded. Please try again later.",
                "retry_after_seconds": max(0, req_ttl)
            }
        )

    return {
        "allowed": True,
        "remaining_requests": MAX_REQ_PER_HOUR - current_reqs,
        "remaining_tokens": MAX_TOKENS_PER_HOUR - current_tokens,
        "reset_in_seconds": req_ttl
    }

async def record_tokens(redis: Redis, user_id: int, tokens_used: int):
    token_key = f"rate_limit:user:{user_id}:tokens"
    new_total = await redis.incrby(token_key, tokens_used)
    if new_total == tokens_used:  # pehli baar token record ho raha hai
        await redis.expire(token_key, WINDOW_SECONDS)
