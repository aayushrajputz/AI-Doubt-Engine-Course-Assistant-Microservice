from typing import TypedDict

class AgentState(TypedDict):
    question : str
    course_id : int

    is_safe : bool
    refusal_reason : str

    context : str

    answer : str

    token_used : int
    cached : bool