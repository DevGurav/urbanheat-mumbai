from langchain_groq import ChatGroq
from app.config import settings


# Initialize Groq LLM

llm = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0,
    max_tokens=1024
)



def generate_response(prompt: str):

    response = llm.invoke(
        prompt
    )

    return response.content