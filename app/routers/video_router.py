from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select                          # DB queries ke liye
from app.core.database import get_db                   # session dependency
from app.models.video_model import Video, VideoChapter # dono models
from app.schemas.video_schema import (                 # dono schemas
    VideoCreate, VideoResponse,
    ChapterCreate, ChapterResponse
)
from sqlalchemy import func, delete
from app.models.doubt_model import Doubt
from app.schemas.video_schema import HotSpotResponse
import json

from app.services.transcript_service import(
    extract_youtube_video_id,
    fetch_youtube_transcript,
    stream_generate_chapters
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

@router.post("/{video_id}/chapters/bulk",response_model=list[ChapterResponse],status_code=status.HTTP_201_CREATED)
async def add_bulk_chapters(
    video_id: int,
    chapters:list[ChapterCreate],
    session:AsyncSession=Depends(get_db)
):
    video_query = select(Video).where(Video.id == video_id)
    result = await session.execute(video_query)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = f"Video not found with this {video_id}"
        ) 
    
    sorted_chapters = sorted(chapters,key=lambda c : c.start_time)

    for i in range(1,len(sorted_chapters)):
        if sorted_chapters[i].start_time < sorted_chapters[i-1].end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Overlaping chapters detected: '{sorted_chapters[i-1].title}' and '{sorted_chapters[i].title}' overlap!"
            ) 
     
    db_chapters = []

    for chapter in sorted_chapters:
        concepts_str = ",".join(chapter.key_concepts) if chapter.key_concepts else ""
        new_chapter = VideoChapter(
            video_id = video_id,
            title = chapter.title,
            start_time = chapter.start_time,
            end_time = chapter.end_time,
            summary = chapter.summary,
            key_concepts = concepts_str
        )

        db_chapters.append(new_chapter)
    
    session.add_all(db_chapters)
    await session.commit()
    
    for chapter in db_chapters:
        await session.refresh(chapter)
    
    return db_chapters


@router.get("/{video_id}/hotspots", response_model=list[HotSpotResponse])
async def get_hotspots(
    video_id: int,
    session: AsyncSession = Depends(get_db)
):
    video_query = select(Video).where(Video.id == video_id)
    video_result = await session.execute(video_query)
    if not video_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found with this {video_id}"
        )

    query = (
        select(
            VideoChapter.id.label("chapter_id"),
            VideoChapter.title.label("chapter_title"),
            VideoChapter.start_time,
            VideoChapter.end_time,
            func.count(Doubt.id).label("doubt_count")
        )
        .join(
            Doubt,
            (Doubt.video_id == VideoChapter.video_id)
            & (Doubt.timestamp >= VideoChapter.start_time)
            & (Doubt.timestamp <= VideoChapter.end_time),
            isouter=True
        )
        .where(VideoChapter.video_id == video_id)
        .group_by(VideoChapter.id)
        .order_by(func.count(Doubt.id).desc())
    )

    result = await session.execute(query)
    payload = result.all()

    hotspots = [
        HotSpotResponse(
            chapter_id=row.chapter_id,
            chapter_title=row.chapter_title,
            start_time=row.start_time,
            end_time=row.end_time,
            doubt_count=row.doubt_count
        )
        for row in payload
    ]

    return hotspots

@router.delete("/{video_id}",status_code=status.HTTP_200_OK)
async def delete_video(
    video_id:int,
    session:AsyncSession = Depends(get_db)
):
    video_query = select(Video).where(Video.id == video_id)
    result = await session.execute(video_query)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with this id{video_id} not found"
        )
    await session.execute(
        delete(VideoChapter).where(VideoChapter.video_id == video_id)
    )
    await session.execute(
        delete(Doubt).where(Doubt.video_id == video_id)
    )
    await session.delete(video) 
    await session.commit()

    return{"message": f"Video #{video_id} and its chapters deleted successfully"}


@router.post("/{video_id}/auto-chapters-stream")
async def auto_generate_chapters_stream(
    video_id: int, 
    session: AsyncSession = Depends(get_db)
):
    """
    REAL-TIME SSE STREAMING FOR CHAPTERS:
    Har chapter generate hote hi stream hoga aur real-time me DB me insert hoga!
    """
    video_query = select(Video).where(Video.id == video_id)
    result = await session.execute(video_query)
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="video is not found")

    yt_id = extract_youtube_video_id(video.url)
    if not yt_id:
        raise HTTPException(status_code=400, detail="Valid youtube url is required")

    try:
        transcript = fetch_youtube_transcript(yt_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Pehle purane chapters saaf karo taaki fresh save hon
    await session.execute(delete(VideoChapter).where(VideoChapter.video_id == video_id))
    await session.commit()

    duration = video.duration_seconds or 1800

    async def chapter_generator():
        yield "data: [STARTING_AI_TRANSCRIPTION]\n\n"
        
        async for ch in stream_generate_chapters(transcript, total_duration_seconds=duration):
            # 1. DB me save karo instantly
            concepts = ch.get("key_concepts", [])
            concepts_str = ",".join(concepts) if isinstance(concepts, list) else str(concepts)
            
            db_chapter = VideoChapter(
                video_id=video_id,
                title=ch.get("title", "Lecture Section"),
                start_time=ch.get("start_time", 0),
                end_time=ch.get("end_time", 300),
                summary=ch.get("summary", ""),
                key_concepts=concepts_str
            )
            session.add(db_chapter)
            await session.commit()
            await session.refresh(db_chapter)

            # 2. SSE line yield karo with DB id!
            event_data = {
                "id": db_chapter.id,
                "video_id": video_id,
                "title": db_chapter.title,
                "start_time": db_chapter.start_time,
                "end_time": db_chapter.end_time,
                "summary": db_chapter.summary,
                "key_concepts": ch.get("key_concepts", [])
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(chapter_generator(), media_type="text/event-stream")

    return StreamingResponse(chapter_generator(), media_type="text/event-stream")

