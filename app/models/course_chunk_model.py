from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text
from app.models.doubt_model import Base


class CourseChunk(Base):
    __tablename__ = "course_chunks"


    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    video_id : Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    course_id : Mapped[int] = mapped_column(Integer,index=True, nullable=False)
    content : Mapped[str] = mapped_column(Text,nullable=False)
    embedding : Mapped[list[float]] = mapped_column(Vector(768),nullable=False)
    timestamp: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    