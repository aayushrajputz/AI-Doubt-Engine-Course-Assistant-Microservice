from langgraph.graph import StateGraph, START, END
import tiktoken
from app.ai.state import AgentState
from app.ai.sanitizers import sanitize_user_prompt
import os
from groq import AsyncGroq
from dotenv import load_dotenv
import json

load_dotenv()
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


tokenizer = tiktoken.get_encoding("cl100k_base")

def calculate_cost(input_token : int, output_tokens: int) -> dict:
    cost_usd = (input_token/ 1_000_000 *0.15) + (output_tokens/ 1_000_000 *0.50)
    cost_inr = cost_usd * 84.0
    
    return {"usd": cost_usd, "inr": cost_inr}
    
def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text))


async def guardrail_node(state: AgentState) -> dict:
    is_safe, reason = sanitize_user_prompt(state["question"])
    return {"is_safe": is_safe, "refusal_reason": reason}


async def refusal_node(state: AgentState) -> dict:
    msg = f"I cannot fulfill this request. Reason: {state['refusal_reason']}"
    return {"answer": msg, "token_used": count_tokens(msg)}


async def retriever_node(state: AgentState) -> dict:
    context = (
        f"[Course {state['course_id']} Knowledge Base]: "
        f"HNSW uses proximity graphs where ef_construction controls the trade-off "
        f"between index build time and search accuracy."
    )
    return {"context": context}
SYSTEM_PROMPT = """You are LearnTube's Senior AI Doubt Resolution Engineer.
Your goal is to explain technical concepts to learners with deep architectural clarity.
Always structure your answers with:
1. Core Concept & The 'Why'
2. Real-World Execution / Code example
3. Common Production Pitfalls

Strictly use the provided Course Context to answer the question."""


async def tutor_node(state: AgentState) -> dict:
    user_prompt = f"Course Context: {state['context']}\n\nLearner Doubt: {state['question']}"
    
    response = await groq_client.chat.completions.create(
        model="openai/gpt-oss-120b", 
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=800
    )
    
    answer_text = response.choices[0].message.content
    tokens = count_tokens(answer_text) + count_tokens(user_prompt)
    
    return {"answer": answer_text, "token_used": tokens}



def safety_router(state: AgentState) -> str:
    if state["is_safe"]:
        return "retriever_node"
    return "refusal_node"


async def stream_doubt_answer(question : str, course_id : int):
    full_answer = []
    is_safe, reason = sanitize_user_prompt(question)
    if not is_safe:
        yield f"data: I cannot answer this query. Reason: {reason}\n\n"
        yield "data: [DONE]\n\n"
        return 

    prompt = f"Learner Question: {question}"
    input_tokens = count_tokens(prompt) + count_tokens(SYSTEM_PROMPT)

    stream = await groq_client.chat.completions.create(
        model = "openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt} 
        ],
        temperature = 0.1,
        max_tokens = 800,
        stream = True,
    )
    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            full_answer.append(token)
            yield f"data: {token}\n\n"

    complete_text = "".join(full_answer)
    output_tokens = count_tokens(complete_text)
    costs = calculate_cost(input_tokens, output_tokens)

    metrics = {
        "event": "usage_metrics",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_inr": f"₹{costs['inr']}",
        "cost_usd": f"${costs['usd']}"
    }
    yield f"data: {json.dumps(metrics)}\n\n"
    yield "data: [DONE]\n\n"

    if redis and cache_key:
        await redis.set(cache_key, complete_text, ex=86400)     


 
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
        "refusal_node": "refusal_node"
    }
)

workflow.add_edge("retriever_node", "tutor_node")
workflow.add_edge("tutor_node", END)
workflow.add_edge("refusal_node", END)

tutor_graph = workflow.compile()
