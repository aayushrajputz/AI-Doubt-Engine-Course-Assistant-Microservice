import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Gemini Client initialize
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def get_embedding(text: str) -> list[float]:
    """
    Converts English text into a 768-dimensional float vector.
    """
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text.replace("\n", " "),
        config = {"output_dimensionality" : 768}
    )
    return response.embeddings[0].values
   