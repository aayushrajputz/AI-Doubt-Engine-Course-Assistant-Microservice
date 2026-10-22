from app.ai.state import AgentState
from app.core.database import async_session
from app.repositories.course_chunk_repository import CourseChunkRepository
from app.services.embedding_service import get_embedding

chunk_repo = CourseChunkRepository()

async def retriever_node(state: AgentState) -> dict:
    question = state["question"]
    course_id = state["course_id"]

    query_vector = await get_embedding(question)
    async with async_session() as session:
        results = await chunk_repo.hybrid_search(
            session=session,
            course_id=course_id,
            query_vector=query_vector,
            query_text=question,
            k=60,
            limit=2
        )

    if results:
        context_parts = [f"- {chunk.content}" for chunk, score in results]
        context = "\n".join(context_parts)
    else:
        context = "No specific course lecture notes found for this topic."

    return {"context": context}
