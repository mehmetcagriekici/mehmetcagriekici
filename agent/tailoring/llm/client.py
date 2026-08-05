import os

from ollama import AsyncClient, ChatResponse

# Ollama host - defaults to localhost:11434 for local development
# When running in Docker, set OLLAMA_HOST env var to http://ollama:11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

_client = AsyncClient(host=OLLAMA_HOST)


class OllamaError(Exception):
    """Raised when an Ollama chat call fails for any reason -- a bad response
    (e.g. the model isn't pulled), an unreachable host, a timeout (the likely
    case in practice: this project runs CPU-only inference, see ../../CLAUDE.md's
    tech stack section), or anything else the client library raises."""


# async function to get llm response from ollama
async def llm_ollama(user_prompt: str, system_prompt: str, model: str = "gemma3", temperature: float = 0.2) -> str:
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
    except Exception as e:
        # Not logged here -- raise OllamaError(...) from e preserves the original
        # exception (type and message) on __cause__, so whoever ends up catching
        # and logging this (see tailoring/generate.py) gets the full chain in one
        # log line rather than this call logging it again on top.
        raise OllamaError(str(e)) from e
