from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime
from typing import Optional

class VideoCreate(BaseModel):
    title: str = Field(..., min_length=3, description="video title")
    url: str = Field(..., description="video url")
    course_id: int = Field(..., gt=0, description="course id")
    description: Optional[str] = Field(default=None, description="video description")
    duration_seconds: Optional[int] = Field(default=None, ge=0, description="video duration in seconds")

class VideoResponse(BaseModel):
    id: int
    title: str
    url: str
    course_id: int
    description: Optional[str] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChapterCreate(BaseModel):
    title: str = Field(..., min_length=3, description="chapter title")
    start_time: int = Field(..., ge=0, description="chapter start time in seconds")
    end_time: int = Field(..., ge=0, description="chapter end time in seconds")
    summary: str = Field(..., min_length=5, description="chapter summary")
    key_concepts: list[str] = Field(default=[], description="chapter key concepts")

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self

class ChapterResponse(BaseModel):
    id: int
    video_id: int
    title: str
    start_time: int
    end_time: int
    summary: str
    key_concepts: list[str] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("key_concepts", mode="before")
    @classmethod
    def convert_key_concepts(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v