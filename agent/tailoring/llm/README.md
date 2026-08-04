# llm

Ollama client wrapper — the only place `tailoring/` actually talks to the local model.

`llm_ollama(user_prompt: str, system_prompt: str, model: str = "gemma3", temperature: float = 0.2) -> str | None` in `client.py` sends one `system` message and one `user` message via a **module-level, reused** `AsyncClient` (not one constructed per call — verified 2026-08-04) with `options={"temperature": temperature}` (kept low by default since these calls need to stay factual, not creative), and returns `response.message.content`, or `None` (logged) on failure. Deliberately generic — it doesn't know or care which of the three calls (resume, cover letter, application/form-fields) it's serving; `prompts/` builds the specific `user_prompt` for each, and the caller invokes this function three times per posting (decided 2026-08-04 — see `../README.md`).

**Failure handling distinguishes three cases (decided 2026-08-04, verified against the installed library's actual source, not guessed):**
- `ResponseError` — the Ollama server responded with an HTTP error (bad model name, bad request); logs its `.status_code` and `.error`.
- `ConnectionError` (built-in, not `httpx.ConnectError`) — Ollama itself catches `httpx.ConnectError` internally and re-raises it as a plain `ConnectionError`, so that's what this code has to catch, not the `httpx` exception directly.
- `httpx.TimeoutException` — not wrapped by the library, propagates as-is.
- Anything else falls through to a generic catch-all.

All three still return `None` to the caller — the distinction is for the logs, not the return type. `write/` (or whatever calls this) only ever sees "got a string" or "got `None`."

**Dependency: `ollama` (added 2026-08-04)** — declared in `../../pyproject.toml`, installed in `../../venv`, frozen in `../../requirements.txt`. Previously imported but not installed or declared anywhere; running any code that imported this module would have failed with `ModuleNotFoundError`.

Named `client.py`, not `ollama.py` — the latter would shadow the `ollama` pip package for any absolute import inside this file (`from ollama import AsyncClient` importing itself instead of the real package).

`OLLAMA_HOST` env var controls the target host, defaulting to `http://localhost:11434` for local dev; set to `http://ollama:11434` (or equivalent) when running under the project's planned k3s/minikube deployment (see the Architecture section of `../../CLAUDE.md`).

Scratch/prototype — role names and the single-string return format may still change as `prompts/` and `write/` firm up. See `../README.md`.
