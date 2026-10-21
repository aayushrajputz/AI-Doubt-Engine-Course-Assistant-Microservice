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



router  = APIRouter(prefix="/doubts",tags=["doubts"])

repo = DoubtRepository()

@router.post("/", response_model=DoubtResponse, status_code=status.HTTP_201_CREATED)
async def create_doubt(
    payload: DoubtCreate,               
    db: AsyncSession = Depends(get_db)  
):
    
    new_doubt = Doubt(
        title=payload.title,
        question=payload.question,
        course_id=payload.course_id,
        tags=",".join(payload.tags)
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
    db: AsyncSession = Depends(get_db)
):
    doubt = await repo.get_by_id(db, doubt_id)
    if doubt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doubt not found with this {doubt_id}")

    return StreamingResponse(
        stream_doubt_answer(doubt.question, doubt.course_id),
        media_type="text/event-stream"
    )

    
