# llm

Ollama client wrapper — the only place `tailoring/` talks to the local model.

`llm_ollama(user_prompt, system_prompt, model="gemma3", temperature=0.2) -> str` in `client.py` sends one `system` message and one `user` message via a module-level, reused `AsyncClient`, with a low default temperature (these calls need to stay factual, not creative), and returns `response.message.content`. Deliberately generic — it doesn't know which of the three calls (resume, cover letter, application) it's serving; `prompts/` builds the specific `user_prompt`, and the caller invokes this function three times per posting.

**Failure handling:** any failure (bad model name, connection error, timeout — the one expected in practice, given CPU-only inference) is caught by one `except Exception` and re-raised as `OllamaError`. The caller must handle this explicitly — there's no `None` return to check. `raise OllamaError(str(e)) from e` preserves the original exception as `__cause__`, so whichever `except OllamaError` finally logs it gets the full chain in one call; this function doesn't log itself, to avoid double-logging.

**Dependency:** `ollama`, declared in `../../pyproject.toml`, installed in `../../venv`, frozen in `../../requirements.txt`.

Named `client.py`, not `ollama.py` — the latter would shadow the `ollama` pip package for any absolute import inside this file.

`OLLAMA_HOST` env var controls the target host, defaulting to `http://localhost:11434` for local dev; set to `http://ollama:11434` (or equivalent) under the planned k3s/minikube deployment.

Scratch/prototype — role names and the return format may still change as `prompts/` and `write/` firm up. See `../README.md`.
