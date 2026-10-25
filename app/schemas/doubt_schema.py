from pydantic import BaseModel , Field, field_validator
from pydantic import ConfigDict

class DoubtCreate(BaseModel):
    user_id : int = Field(default=1, gt=0, title = "user id")
    title : str = Field(..., min_length = 5, title = "doubt title")
    question : str = Field(..., title = "question")
    course_id : int = Field(..., gt=0, title = "course id")
    tags : list[str] = []

    @field_validator("title")
    @classmethod
    def validate_title(cls,v:str)-> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Title must be atleast 5 character")
        return v 

     
        
class DoubtResponse(BaseModel):
    user_id : int
    id : int
    title : str
    question : str
    course_id : int
    tags : list[str]
    status : str
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def convert_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v 