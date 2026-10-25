from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.doubt_model import Doubt
from app.schemas.doubt_schema import DoubtResponse
from app.repositories.doubt_repository import DoubtRepository
from app.schemas.doubt_schema import DoubtCreate, DoubtResponse
from fastapi.responses import StreamingResponse
from app.ai.orchestrator import groq_client, SYSTEM_PROMPT 
from app.ai.orchestrator import stream_doubt_answer
from fastapi import Request
import json
from app.services.embedding_service import get_embedding
from app.repositories.course_chunk_repository import CourseChunkRepository
from app.core.rate_limiter import check_rate_limit, record_tokens


router  = APIRouter(prefix="/doubts",tags=["doubts"])
 
repo = DoubtRepository()
chunk_repo = CourseChunkRepository()

@router.post("/", response_model=DoubtResponse, status_code=status.HTTP_201_CREATED)
async def create_doubt(
    payload: DoubtCreate,
    db: AsyncSession = Depends(get_db)  
):
    # Doubt ka embedding generate karo semantic matching ke liye
    q_embedding = await get_embedding(payload.question)

    new_doubt = Doubt(
        user_id =payload.user_id,
        title=payload.title,
        question=payload.question,
        course_id=payload.course_id,
        tags=",".join(payload.tags),
        embedding=q_embedding,
    )
    created_doubt = await repo.create(db, new_doubt)
    return created_doubt



@router.get("/{doubt_id}", response_model=DoubtResponse, status_code=status.HTTP_200_OK)
async def get_doubt(
    doubt_id: int ,
    db: AsyncSession = Depends(get_db)
):

 doubt = await repo.get_by_id(db, doubt_id)
 if doubt is None :
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doubt not found with this {doubt_id}")

 return doubt

@router.post("/{doubt_id}/stream")
async def stream_doubt(
    doubt_id: int,
    request : Request,
    db: AsyncSession = Depends(get_db)
):
    redis = request.app.state.redis  
    doubt = await repo.get_by_id(db, doubt_id)
    if not doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")

    
    # 1. Exact Cache Check (Redis Hot Path)
    cache_key = f"doubt_cache:{doubt.course_id}:{doubt.id}"
    cached_answer = await redis.get(cache_key)
    if cached_answer:
        async def stream_cached():
            yield "data: [EXACT CACHE HIT]\n\n"
            for line in cached_answer.splitlines(keepends=True):
                yield f"data: {line}\n\n"
            

            metrics = { 
                "event": "usage_metrics",
                "cached": True,
                "cache_type": "exact_redis",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_inr": "₹0.00",
                "cost_usd": "$0.0000"
            }
            yield f"data: {json.dumps(metrics)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(stream_cached(), media_type="text/event-stream")

    # 2. Semantic Cache Check (Postgres HNSW Vector Matching)
    if doubt.embedding:
        similar_result = await chunk_repo.find_semantically_similar_doubts(
            session=db,
            course_id=doubt.course_id,
            query_vector=doubt.embedding,
            threshold=0.85,
        )
        if similar_result:
            matched_doubt, similarity = similar_result
            # Is doubt ka bhi ai_answer update kar do DB me
            doubt.ai_answer = matched_doubt.ai_answer
            await db.commit()
            await redis.set(cache_key, matched_doubt.ai_answer, ex=86400)

            async def stream_semantic():
                yield f"data: [SEMANTIC CACHE HIT ({similarity:.1%})]\n\n"
                for line in matched_doubt.ai_answer.splitlines(keepends=True):
                    yield f"data: {line}\n\n"


                metrics = {
                    "event": "usage_metrics",
                    "cached": True,
                    "cache_type": "semantic_vector",
                    "matched_doubt_id": matched_doubt.id,
                    "similarity": round(similarity, 4),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_inr": "₹0.00",
                    "cost_usd": "$0.0000"
                }
                yield f"data: {json.dumps(metrics)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream_semantic(), media_type="text/event-stream")

    # 3. Cache Miss: LLM Inference (Rate limit check runs here so cache hits remain free)
    await check_rate_limit(redis, doubt.user_id)

    async def stream_and_save():
        full_text = []
        async for chunk in stream_doubt_answer(doubt.question, doubt.course_id, redis=redis, cache_key=cache_key):
            if chunk.startswith("data: ") and not chunk.startswith("data: {") and not "[DONE]" in chunk:
                full_text.append(chunk.replace("data: ", "").replace("\n\n", ""))
            
            # Agar metrics ka event aaya, toh user ke tokens record kar lo!
            if '"event": "usage_metrics"' in chunk:
                try:
                    metrics_data = json.loads(chunk.replace("data: ", "").strip())
                    tokens = metrics_data.get("total_tokens", 0)
                    if tokens > 0:
                        await record_tokens(redis, doubt.user_id, tokens)
                except Exception:
                    pass
            
            yield chunk

        # DB me save karo taaki future me semantic search ho sake
        generated_answer = "".join(full_text).strip()
        if generated_answer:
            doubt.ai_answer = generated_answer
            await db.commit()

    return StreamingResponse(stream_and_save(), media_type="text/event-stream")





    
