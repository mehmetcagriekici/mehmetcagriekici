import os

from ollama import AsyncClient, ChatResponse

# Ollama host - defaults to localhost:11434 for local development
# When running in Docker, set OLLAMA_HOST env var to http://ollama:11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# qwen2.5:14b (Q4_K_M, ~9 GB) -- upgraded 2026-09-30 from qwen2.5:latest
# (7.6B) after live runs showed the 7B ignoring prompt-only honesty rules
# about half the time. Same family, so the JSON-schema behavior carries over.
# The largest model that fits this machine comfortably (30 GB RAM, laptop
# CPU): a 32B would need ~24 GB and run at ~1 token/s. Roughly half the 7B's
# speed -- accepted, slow is fine for this pipeline.
DEFAULT_MODEL = "qwen2.5:14b"

# Hard cap on generated tokens per call. This, not the timeout below, is what
# actually stops a runaway generation: a client-side timeout only abandons the
# request on the Python side, while the Ollama server keeps generating and keeps
# holding its only slot (Ollama serving one request at a time: observed as -np 1
# on this machine, pinned via OLLAMA_NUM_PARALLEL=1 per ../../README.md), stalling every other call
# queued behind it. A generous guess for the largest output (the resume JSON),
# not a measured bound -- tune once real output lengths have been logged.
NUM_PREDICT = 2048

# Context window per call, in tokens (prompt + output). Ollama loaded
# qwen2.5 with 4096 by default and silently dropped whatever didn't fit: a
# 2026-09-30 cover-letter prompt of ~25,700 characters had only 2,050 prompt
# tokens evaluated, so the job posting itself never reached the model (it
# invented the company name). 16384 fits a ~7k-token prompt plus NUM_PREDICT
# with room to spare; qwen2.5 supports up to 32768. Costs ~1 GB more RAM for
# the KV cache and slower prompt processing on CPU.
NUM_CTX = 16384

# Seconds before the Python side gives up on a call. Deliberately generous
# (slow is accepted for this pipeline): the 7B already took ~9 min per cover
# letter with the 16k context, the 14B is roughly twice as slow, and time spent
# waiting in Ollama's single-slot queue behind other calls counts against this
# too.
TIMEOUT_SECONDS = 3600

_client = AsyncClient(host=OLLAMA_HOST, timeout=TIMEOUT_SECONDS)


class OllamaError(Exception):
    """Raised when an Ollama chat call fails for any reason -- a bad response
    (e.g. the model isn't pulled), an unreachable host, a timeout (the likely
    case in practice: this project runs CPU-only inference, see ../../CLAUDE.md's
    tech stack section), output cut off at NUM_PREDICT, or anything else the
    client library raises."""


# async function to get llm response from ollama.
# response_schema: JSON schema the output is constrained to (Ollama structured
# outputs) -- every call in this pipeline expects JSON, so it's required rather
# than optional. Constraining decoding rules out code fences, prose around the
# JSON, and keys outside the schema, instead of only detecting them afterwards.
async def llm_ollama(
    user_prompt: str,
    system_prompt: str,
    response_schema: dict,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> str:
    try:
        response: ChatResponse = await _client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format=response_schema,
            options={
                "temperature": temperature,
                "num_predict": NUM_PREDICT,
                "num_ctx": NUM_CTX,
            },
        )
    except Exception as e:
        # Not logged here -- raise OllamaError(...) from e preserves the original
        # exception (type and message) on __cause__, so whoever ends up catching
        # and logging this (see tailoring/generate.py) gets the full chain in one
        # log line rather than this call logging it again on top.
        raise OllamaError(str(e)) from e

    # Hitting the cap means the JSON was cut off mid-object. Raised here as its
    # own failure rather than left to surface later as a confusing INVALID_JSON.
    if response.done_reason == "length":
        raise OllamaError(f"output cut off at num_predict={NUM_PREDICT} tokens")

    return response.message.content
