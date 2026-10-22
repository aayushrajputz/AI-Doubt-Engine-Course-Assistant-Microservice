import json
import tiktoken
from langgraph.graph import StateGraph, START, END
from app.ai.state import AgentState
from app.ai.sanitizers import sanitize_user_prompt
from app.ai.nodes import (
    guardrail_node,
    refusal_node,
    retriever_node,
    tutor_node,
    SYSTEM_PROMPT,
    groq_client,
)

tokenizer = tiktoken.get_encoding("cl100k_base")

def calculate_cost(input_tokens: int, output_tokens: int) -> dict:
    cost_usd = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
    cost_inr = cost_usd * 84.0
    return {"usd": round(cost_usd, 6), "inr": round(cost_inr, 4)}

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text))


def safety_router(state: AgentState) -> str:
    if state["is_safe"]:
        return "retriever_node"
    return "refusal_node"


workflow = StateGraph(AgentState)

workflow.add_node("guardrail_node", guardrail_node)
workflow.add_node("retriever_node", retriever_node)
workflow.add_node("tutor_node", tutor_node)
workflow.add_node("refusal_node", refusal_node)

workflow.add_edge(START, "guardrail_node")

workflow.add_conditional_edges(
    "guardrail_node",
    safety_router,
    {
        "retriever_node": "retriever_node",
        "refusal_node": "refusal_node",
    },
)

workflow.add_edge("retriever_node", "tutor_node")
workflow.add_edge("tutor_node", END)
workflow.add_edge("refusal_node", END)

tutor_graph = workflow.compile()

# Real-Time SSE Token Streamer
async def stream_doubt_answer(question: str, course_id: int,redis=None,cache_key: str=None):
    full_answer = []
    is_safe, reason = sanitize_user_prompt(question)
    if not is_safe:
        yield f"data: I cannot answer this query. Reason: {reason}\n\n"
        yield "data: [DONE]\n\n"
        return

    prompt = f"Learner Question: {question}"
    input_tokens = count_tokens(prompt) + count_tokens(SYSTEM_PROMPT)

    stream = await groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=800,
        stream=True,
    )
    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            full_answer.append(token)
            yield f"data: {token}\n\n"

    complete_text = "".join(full_answer)
    output_tokens = count_tokens(complete_text)
    costs = calculate_cost(input_tokens, output_tokens)
    if redis and cache_key:
        await redis.set(cache_key, complete_text, ex=86400)

    metrics = {
        "event": "usage_metrics",
        "cached": False,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_inr": f"₹{costs['inr']}",
        "cost_usd": f"${costs['usd']}",
    }
    yield f"data: {json.dumps(metrics)}\n\n"
    yield "data: [DONE]\n\n"

