import logging
import os
from ollama import AsyncClient
from ollama import ChatResponse

# Ollama host - defaults to localhost:11434 for local development
# When running in Docker, set OLLAMA_HOST env var to http://ollama:11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# async function to get llm response from ollama
async def llm_ollama(user_prompt: str, system_prompt: str, model: str = "gemma3", temperature: float = 0.2) -> str | None:
    try:
        response: ChatResponse = await AsyncClient(host=OLLAMA_HOST).chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature},
        )
        return response.message.content
    except Exception as e:
        logging.error("ollama chat call failed: %s", e)
        return None
