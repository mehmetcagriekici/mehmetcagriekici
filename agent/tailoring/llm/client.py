import logging
import os

import httpx
from ollama import AsyncClient, ChatResponse, ResponseError

# Ollama host - defaults to localhost:11434 for local development
# When running in Docker, set OLLAMA_HOST env var to http://ollama:11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

_client = AsyncClient(host=OLLAMA_HOST)

logger = logging.getLogger(__name__)

# async function to get llm response from ollama
async def llm_ollama(user_prompt: str, system_prompt: str, model: str = "gemma3", temperature: float = 0.2) -> str | None:
    try:
        response: ChatResponse = await _client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature},
        )
        return response.message.content
    except ResponseError as e:
        logger.error("ollama returned an error response (status %s): %s", e.status_code, e.error)
        return None
    except ConnectionError as e:
        logger.error("could not reach ollama at %s: %s", OLLAMA_HOST, e)
        return None
    except httpx.TimeoutException as e:
        logger.error("ollama request to %s timed out: %s", OLLAMA_HOST, e)
        return None
    except Exception as e:
        logger.error("ollama chat call failed unexpectedly: %s", e)
        return None
