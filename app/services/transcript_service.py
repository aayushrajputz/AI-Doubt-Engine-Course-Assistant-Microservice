import re
import json
import asyncio
from youtube_transcript_api import YouTubeTranscriptApi
from app.ai.orchestrator import groq_client

def extract_youtube_video_id(url: str) -> str | None:
    """YouTube URL se 11-character video ID extract karta hai."""
    if not url:
        return None
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"embed\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if len(url) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", url):
        return url
    return None


def fetch_youtube_transcript(video_id: str) -> list[dict]:
    """
    YouTube se transcript fetch karta hai:
    1. Try English / Hindi / Hinglish
    2. Fallback to ANY available language on the video
    """
    try:
        ytt = YouTubeTranscriptApi()
        try:
            snippets = ytt.fetch(video_id, languages=['en', 'en-IN', 'hi', 'hi-Latn'])
        except Exception:
            transcript_list = ytt.list(video_id)
            first_transcript = next(iter(transcript_list))
            snippets = first_transcript.fetch()

        results = []
        for s in snippets:
            results.append({
                'text': s.text if hasattr(s, 'text') else str(s.get('text', '')),
                'start': float(s.start if hasattr(s, 'start') else s.get('start', 0.0)),
                'duration': float(s.duration if hasattr(s, 'duration') else s.get('duration', 0.0)),
            })
        return results
    except Exception as e:
        raise RuntimeError(f"Could not fetch transcript for video {video_id}: {str(e)}")


async def _extract_chapters_from_window(window_text: str, window_start: int, window_end: int) -> list[dict]:
    """Ek chhota window Groq ko bhej kar 2-4 chapters generate karwata hai (Tokens safe)."""
    prompt = f"""You are an EdTech video curriculum analyzer.
Below is a specific segment of a video lecture from {window_start}s to {window_end}s.

TRANSCRIPT SEGMENT:
{window_text}

TASK:
Identify 1 to 3 major topic transitions inside this segment ({window_start}s to {window_end}s).

STRICT JSON OUTPUT FORMAT (Return ONLY a raw JSON array. No markdown, no backticks, no comments):
[
  {{
    "title": "Clear Topic Title (e.g. StateGraph Setup)",
    "start_time": {window_start},
    "end_time": {window_end},
    "summary": "Overview of what is taught in this part",
    "key_concepts": ["concept1", "concept2"]
  }}
]

RULES:
1. First chapter start_time must be >= {window_start}
2. Last chapter end_time must be <= {window_end}
3. Title min 3 chars, summary min 5 chars.
4. Return ONLY pure JSON array.
"""
    try:
        response = await groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a JSON-only generating assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        return json.loads(content)
    except Exception:
        return [{
            "title": f"Lecture Segment ({window_start}s - {window_end}s)",
            "start_time": window_start,
            "end_time": window_end,
            "summary": f"Discussion and concepts covering {window_start}s to {window_end}s",
            "key_concepts": ["core concepts"]
        }]


async def stream_generate_chapters(transcript: list[dict], total_duration_seconds: int = 1800):
    """
    STREAMING GENERATOR:
    Har window process hote hi real-time mein chapters yield karta hai!
    Frontend live table mein chapters stream hote hue dekh sakta hai.
    """
    if not transcript:
        return

    max_transcript_time = int(transcript[-1].get('start', 0) + transcript[-1].get('duration', 0))
    total_duration = max(total_duration_seconds, max_transcript_time)

    WINDOW_SIZE = 900  # 15 minutes per batch
    current_idx = 0
    num_entries = len(transcript)

    for win_start in range(0, total_duration, WINDOW_SIZE):
        win_end = min(win_start + WINDOW_SIZE, total_duration)

        window_lines = []
        bucket_time = win_start
        bucket_text = []

        while current_idx < num_entries:
            entry = transcript[current_idx]
            start = int(entry.get('start', 0))
            if start >= win_end:
                break
            
            bucket_text.append(entry.get('text', '').strip())
            if start - bucket_time >= 40:
                window_lines.append(f"[{bucket_time}s - {start}s]: {' '.join(bucket_text)}")
                bucket_text = []
                bucket_time = start
            
            current_idx += 1

        if bucket_text:
            window_lines.append(f"[{bucket_time}s+]: {' '.join(bucket_text)}")

        if not window_lines:
            continue

        window_str = "\n".join(window_lines[:50])

        # Groq se is window ke chapters nikalo
        chapters = await _extract_chapters_from_window(window_str, win_start, win_end)
        
        # Real-time stream each chapter
        for ch in chapters:
            yield ch
            await asyncio.sleep(0.05)


async def generate_chapters_from_transcript(transcript: list[dict], total_duration_seconds: int = 1800) -> list[dict]:
    """Non-streaming helper function."""
    all_chapters = []
    async for ch in stream_generate_chapters(transcript, total_duration_seconds):
        all_chapters.append(ch)
    return all_chapters
