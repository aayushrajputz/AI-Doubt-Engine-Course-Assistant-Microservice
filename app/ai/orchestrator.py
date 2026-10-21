from langgraph.graph import StateGraph, START, END
import tiktoken
from app.ai.state import AgentState
from app.ai.sanitizers import sanitize_user_prompt
import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


tokenizer = tiktoken.get_encoding("cl100k_base")

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
    is_safe, reason = sanitize_user_prompt(question)
    if not is_safe:
        yield f"i cannot ans this ques {reason}\n\n"
        yield "data: Done\n\n"
        return 

    prompt = f"learner Ques{question}"
    stream = await groq_client.chat.completions.create(
        model = "openai/gpt-oss-120b"  ,  
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt} 
        ],
        
        temperature = 0.1,
        max_tokens = 800,
        stream = True ,
    )
    async for chunk in stream :
        token = chunk.choices[0].delta.content
        if token : 
         yield f"data:{token}\n\n" 
    yield "data : Done \n\n"

 
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
