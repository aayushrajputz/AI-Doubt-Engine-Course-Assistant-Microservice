from sqlalchemy.orm import Mapped, mapped_column,DeclarativeBase
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass


class Doubt(Base):
    __tablename__ = "doubts"  # Database mein table ka actual naam
    user_id : Mapped[int] = mapped_column(Integer,nullable=False,index=True,default=1)
    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True) 
    video_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("videos.id"), nullable=True, index=True, default=None)
    title : Mapped[str] = mapped_column(String(150), nullable = False)
    question: Mapped[str] = mapped_column(Text, nullable = False)
    course_id : Mapped[int] = mapped_column(Integer, nullable = False, index = True)
    status : Mapped[str] = mapped_column(String(20), default = "pending", nullable = False )
    ai_answer : Mapped[str | None] = mapped_column(Text, nullable = True, default = None)
    tags : Mapped[str] = mapped_column(String(255), default = "")
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone = True), default = lambda : datetime.now(timezone.utc))
    embedding : Mapped[list[float] | None] = mapped_column(Vector(768), nullable = True, default = None)
    timestamp: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
