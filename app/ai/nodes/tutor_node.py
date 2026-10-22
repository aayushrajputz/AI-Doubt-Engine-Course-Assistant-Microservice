import os
import tiktoken
from groq import AsyncGroq
from dotenv import load_dotenv
from app.ai.state import AgentState

load_dotenv()
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
tokenizer = tiktoken.get_encoding("cl100k_base")

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
    tokens = len(tokenizer.encode(answer_text)) + len(tokenizer.encode(user_prompt))
    return {"answer": answer_text, "token_used": tokens}
