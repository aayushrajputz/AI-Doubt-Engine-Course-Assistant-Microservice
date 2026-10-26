from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.models.video_model import Video, VideoChapter

class ChapterContext(BaseModel):
    video_id: int
    video_title: str
    video_url: str
    chapter_id: int
    chapter_title: str
    start_time: int
    end_time: int
    time_range_formatted: str
    summary: str
    key_concepts: list[str]
    cache_bucket_key: str


def format_seconds_to_time(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


async def resolve_chapter(
    session: AsyncSession,
    video_id: int,
    timestamp: int
) -> Optional[ChapterContext]:

    # 1. Fetch Video
    video_query = select(Video).where(Video.id == video_id)
    v_res = await session.execute(video_query)
    video = v_res.scalar_one_or_none()

    if not video:
        return None

    # 2. Fetch Chapters sorted by start_time
    chapter_query = (
        select(VideoChapter)
        .where(VideoChapter.video_id == video_id)
        .order_by(VideoChapter.start_time.asc())
    )
    ch_res = await session.execute(chapter_query)
    chapters = ch_res.scalars().all()

    # Agar koi chapter nahi hai, fall back to 30s bucket
    if not chapters:
        bucket = (timestamp // 30) * 30
        return ChapterContext(
            video_id=video.id,
            video_title=video.title,
            video_url=video.url,
            chapter_id=0,
            chapter_title="Full Video (No Chapters)",
            start_time=0,
            end_time=video.duration_seconds or 0,
            time_range_formatted=f"{format_seconds_to_time(bucket)} - {format_seconds_to_time(bucket + 30)}",
            summary=video.description or "General video discussion",
            key_concepts=[],
            cache_bucket_key=f"video:{video.id}:bucket:{bucket}"
        )

    matched_chapter = None

    # Priority 1: Exact interval match
    for ch in chapters:
        if ch.start_time <= timestamp <= ch.end_time:
            matched_chapter = ch
            break

    # Priority 2: Fuzzy Buffer (±30 seconds)
    if not matched_chapter:
        for ch in chapters:
            if (ch.start_time - 30) <= timestamp <= (ch.end_time + 30):
                matched_chapter = ch
                break

    # Priority 3: Nearest Absolute Distance Fallback
    if not matched_chapter:
        matched_chapter = min(
            chapters,
            key=lambda ch: min(abs(ch.start_time - timestamp), abs(ch.end_time - timestamp))
        )

    concepts = [c.strip() for c in matched_chapter.key_concepts.split(",") if c.strip()]
    formatted_time = f"{format_seconds_to_time(matched_chapter.start_time)} - {format_seconds_to_time(matched_chapter.end_time)}"

    return ChapterContext(
        video_id=video.id,
        video_title=video.title,
        video_url=video.url,
        chapter_id=matched_chapter.id,
        chapter_title=matched_chapter.title,
        start_time=matched_chapter.start_time,
        end_time=matched_chapter.end_time,
        time_range_formatted=formatted_time,
        summary=matched_chapter.summary,
        key_concepts=concepts,
        cache_bucket_key=f"video:{video.id}:chapter:{matched_chapter.id}"
    )