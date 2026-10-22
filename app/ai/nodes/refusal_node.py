import tiktoken
from app.ai.state import AgentState

tokenizer = tiktoken.get_encoding("cl100k_base")

async def refusal_node(state: AgentState) -> dict:
    msg = f"I cannot fulfill this request. Reason: {state['refusal_reason']}"
    tokens = len(tokenizer.encode(msg))
    return {"answer": msg, "token_used": tokens}
