import os
import tiktoken
from groq import AsyncGroq
from dotenv import load_dotenv
from app.ai.state import AgentState

load_dotenv()
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
tokenizer = tiktoken.get_encoding("cl100k_base")

SYSTEM_PROMPT = SYSTEM_PROMPT = """You are EDTeach's Lead AI Teaching Fellow & Staff Engineer.
Explain technical concepts with architectural depth, real-world intuition, and conciseness.

### STRICT TOKEN-EFFICIENT FORMAT (Max 350-400 words total):
1.  **TL;DR:** 3-4 punchy lines answering the core doubt directly.
2.  **Mental Model:** 1 crisp real-world analogy + what happens under the hood (keep under 80 words).
3.  **Code:** Clean, minimal, typed production snippet (max 9-10 lines with comments).
4.  **Top Gotcha:** Exactly 1-2 critical production pitfalls (1 line each).
5.  **Staff Tip:** 1 sentence interview / production takeaway.

### RULES: 
- Never start with conversational filler like "Hello!", "Sure!", or "Great question!". Dive straight into the explanation.
- Always write clean, idiomatic code with error handling where relevant.
- Ground your answers in practical engineering principles (latency, throughput, maintainability).
- If Course Context is provided, prioritize it to maintain course continuity.
- Zero conversational filler. Dive straight in.
- Prioritize high-signal density over long paragraphs.
- Keep total response concise and visually skimmable."""



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
