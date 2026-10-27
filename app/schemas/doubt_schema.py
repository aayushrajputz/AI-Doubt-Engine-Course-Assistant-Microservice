from pydantic import BaseModel , Field, field_validator,ConfigDict,model_validator
from typing import Optional

class DoubtCreate(BaseModel):
    user_id : int = Field(default=1, gt=0, title = "user id")
    video_id: Optional[int] = None
    title : str = Field(..., min_length = 5, title = "doubt title")
    question : str = Field(..., title = "question")
    course_id : int = Field(..., gt=0, title = "course id")
    tags : list[str] = []
    timestamp: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls,v:str)-> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Title must be atleast 5 character")
        return v 
    @model_validator(mode="after")
    def validate_video_and_timestamp(self):
        if self.timestamp is not None and self.video_id is None:
            raise ValueError("Timestamp can only be provided when video_id is also provided")
        
        return self

     
        
class DoubtResponse(BaseModel):
    user_id : int
    video_id: Optional[int] = None
    id : int
    title : str
    question : str
    course_id : int
    tags : list[str]
    status : str
    timestamp: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def convert_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v 