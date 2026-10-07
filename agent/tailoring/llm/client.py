import os

import httpx
from ollama import AsyncClient, ChatResponse, ResponseError

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

# Ollama never errors on an oversized prompt -- it silently drops the start
# (see NUM_CTX). Its reported prompt_eval_count can't reliably detect that
# afterwards, since a prefix reused from Ollama's cache isn't counted, so the
# check happens before sending, on a conservative estimate: a token covers at
# least ~3 characters. Measured on real prompts here: ~5.6 characters/token
# (JSON-heavy English), so this only trips well before a real truncation.
MIN_CHARS_PER_TOKEN = 3.0


class OllamaError(Exception):
    """Raised when an Ollama chat call fails for an infrastructure reason -- an
    error response (e.g. the model isn't pulled), an unreachable host, a
    timeout (the likely case in practice: CPU-only inference, see
    ../../CLAUDE.md's tech stack section), or output cut off at NUM_PREDICT.
    Anything else -- a bug in this code, a misuse of the client -- propagates
    as itself instead of being disguised as an Ollama problem."""


class PromptTooLongError(Exception):
    """The prompt (system + user) may not fit in NUM_CTX minus the output cap,
    so Ollama would silently drop part of it. Raised before anything is sent.
    Not an OllamaError: it's a property of this posting's prompt, not of the
    server, and would fail the same way every run."""


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
    prompt_chars = len(system_prompt) + len(user_prompt)
    max_prompt_tokens = NUM_CTX - NUM_PREDICT
    if prompt_chars / MIN_CHARS_PER_TOKEN > max_prompt_tokens:
        raise PromptTooLongError(
            f"prompt is {prompt_chars} characters, which may exceed the "
            f"{max_prompt_tokens}-token prompt budget "
            f"(num_ctx={NUM_CTX} - num_predict={NUM_PREDICT})"
        )

    # A client per call, not one module-level client: its pooled httpx
    # connections belong to the event loop that opened them, so a shared client
    # failed with "Event loop is closed" on the second asyncio.run() -- and that
    # bug was reported as an OllamaError. One extra connection setup per
    # ~15-minute call costs nothing.
    try:
        async with AsyncClient(host=OLLAMA_HOST, timeout=TIMEOUT_SECONDS) as client:
            response: ChatResponse = await client.chat(
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
    # Infrastructure failures only: an error response from the server
    # (ResponseError), an unreachable host (the ollama library raises the
    # builtin ConnectionError), or a transport failure/timeout (httpx). Not
    # logged here -- "from e" keeps the original on __cause__, so whoever
    # catches and logs this (see tailoring/generate.py) gets the full chain once.
    except (ResponseError, ConnectionError, httpx.HTTPError) as e:
        raise OllamaError(f"{type(e).__name__}: {e}") from e

    # Hitting the cap means the JSON was cut off mid-object. Raised here as its
    # own failure rather than left to surface later as a confusing INVALID_JSON.
    if response.done_reason == "length":
        raise OllamaError(f"output cut off at num_predict={NUM_PREDICT} tokens")

    return response.message.content
