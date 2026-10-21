from sqlalchemy.orm import Mapped, mapped_column,DeclarativeBase
from sqlalchemy import String, Integer, DateTime, Text
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class Doubt(Base):
    __tablename__ = "doubts"  # Database mein table ka actual naam

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True) 

    title : Mapped[str] = mapped_column(String(150), nullable = False)

    question: Mapped[str] = mapped_column(Text, nullable = False)

    course_id : Mapped[int] = mapped_column(Integer, nullable = False, index = True)

    status : Mapped[str] = mapped_column(String(20), default = "pending", nullable = False )

    ai_answer : Mapped[str | None] = mapped_column(Text, nullable = True, default = None)

    tags : Mapped[str] = mapped_column(String(255), default = "")

    created_at : Mapped[datetime] = mapped_column(DateTime(timezone = True), default = lambda : datetime.now(timezone.utc))


   

