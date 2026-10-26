from app.ai.state import AgentState
from app.ai.sanitizers import sanitize_user_prompt

async def guardrail_node(state: AgentState) -> dict:
    is_safe, reason = sanitize_user_prompt(state["question"])
    return {"is_safe": is_safe, "refusal_reason": reason}