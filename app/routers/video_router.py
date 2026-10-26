from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select                          # DB queries ke liye
from app.core.database import get_db                   # session dependency
from app.models.video_model import Video, VideoChapter # dono models
from app.schemas.video_schema import (                 # dono schemas
    VideoCreate, VideoResponse,
    ChapterCreate, ChapterResponse
)

router = APIRouter(prefix="/admin/videos", tags=["videos"])


@router.post("/",response_model=VideoResponse,status_code=status.HTTP_201_CREATED)
async def create_video(payload:VideoCreate,session:AsyncSession=Depends(get_db)):
    new_video = Video(
        title=payload.title,
        url=payload.url,
        course_id=payload.course_id,
        description=payload.description,
        duration_seconds=payload.duration_seconds
    )
    session.add(new_video)
    await session.commit()
    await session.refresh(new_video)
    return new_video 

@router.get("/course/{course_id}", response_model=list[VideoResponse])
async def list_videos_by_course(
    course_id: int,
    session: AsyncSession = Depends(get_db)
):
    query = select(Video).where(Video.course_id == course_id)
    result  = await session.execute(query)
    videos = result.scalars().all()
    return videos
@router.post("/{video_id}/chapters",response_model=ChapterResponse,status_code=status.HTTP_201_CREATED)
async def add_chapter(
    video_id:int,
    payload:ChapterCreate,
    session:AsyncSession = Depends(get_db)
):
    video_query = select(Video).where(Video.id == video_id)
    result = await session.execute(video_query)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = f"Video not found with this {video_id}"
        )
    concepts_str = ",".join(payload.key_concepts) if payload.key_concepts else ""

    new_chapter = VideoChapter(
        video_id = video_id,
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
        summary=payload.summary,
        key_concepts=concepts_str
    )
    session.add(new_chapter)
    await session.commit()
    await session.refresh(new_chapter)

    return new_chapter


@router.get("/{video_id}/chapters",response_model=list[ChapterResponse])
async def list_chapters(
    video_id: int,
    session:AsyncSession = Depends(get_db)
):

    query = (
        select(VideoChapter)
        .where(VideoChapter.video_id == video_id)
        .order_by(VideoChapter.start_time.asc())
    )
    result = await session.execute(query)
    chapters = result.scalars().all()

    return chapters 