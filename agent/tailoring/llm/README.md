# llm

Ollama client wrapper — the only place `tailoring/` talks to the local model.

`llm_ollama(user_prompt, system_prompt, response_schema, model=DEFAULT_MODEL, temperature=0.2) -> str` in `client.py` sends one `system` message and one `user` message via a module-level, reused `AsyncClient`, with a low default temperature (these calls need to stay factual, not creative), and returns `response.message.content`. Deliberately generic — it doesn't know which of the three calls (resume, cover letter, application) it's serving; `prompts/` builds the specific `user_prompt`, and the caller invokes this function three times per posting.

**Default model:** `qwen2.5:14b` (Q4_K_M, ~9 GB) — upgraded 2026-09-30 from `qwen2.5:latest` (7.6B) after live runs showed the 7B ignoring prompt-only honesty rules about half the time. Same family, so JSON-schema behavior carries over. The largest model that fits this machine comfortably (30 GB RAM, laptop CPU); a 32B would need ~24 GB at ~1 token/s. Roughly half the 7B's speed — accepted. (Before the 7B: `gemma3`, never pulled on this machine.)

**JSON mode (structured outputs):** `response_schema` is required and passed as Ollama's `format`, so decoding is constrained to that JSON schema — no code fences, no prose around the JSON, no keys outside the schema. The schemas come from `../write/write.py`: `RESUME_JSON_SCHEMA` is generated from the same pydantic model that validates the response; `cover_letter_schema(gaps_expected)` starts from the `CoverLetter` model's schema and makes `gaps` a required field or removes it, depending on whether any known gap applies; and `application_answers_schema(questions)` builds one per posting with exactly the real `field_id`s as required keys (so the placeholder-key failure from the 2026-08-05 run can't recur). `max_length` is deliberately not put in the schema — constrained decoding would enforce it by silently cutting answers off mid-sentence.

**Limits:** `NUM_CTX = 16384` sets the context window explicitly — Ollama's default of 4096 silently dropped most of a ~7k-token cover-letter prompt (only 2,050 prompt tokens were evaluated), including the job posting, so the model invented the company name; 16384 fits the prompt plus the output cap, at the cost of ~1 GB more RAM and slower CPU prompt processing. `NUM_PREDICT = 2048` caps generated tokens per call — this is what actually stops a runaway generation, since Ollama runs with a single slot (`-np 1`) and a stuck call blocks everything queued behind it. Hitting the cap (`done_reason == "length"`) raises `OllamaError` rather than returning truncated JSON. 2048 is a generous guess, not a measured bound. `TIMEOUT_SECONDS = 3600` is the client-side limit — deliberately generous, since slow is accepted: the 7B already took ~9 min per cover letter at 16k context, the 14B is roughly twice as slow, and queue wait counts too; it only abandons the request on the Python side — the server keeps generating until `num_predict`.

**Failure handling:** any failure (bad model name, connection error, timeout — the one expected in practice, given CPU-only inference — or output cut off at `NUM_PREDICT`) is caught by one `except Exception` and re-raised as `OllamaError`. The caller must handle this explicitly — there's no `None` return to check. `raise OllamaError(str(e)) from e` preserves the original exception as `__cause__`, so whichever `except OllamaError` finally logs it gets the full chain in one call; this function doesn't log itself, to avoid double-logging.

**Dependency:** `ollama`, declared in `../../pyproject.toml`, installed in `../../venv`, frozen in `../../requirements.txt`.

Named `client.py`, not `ollama.py` — the latter would shadow the `ollama` pip package for any absolute import inside this file.

`OLLAMA_HOST` env var controls the target host, defaulting to `http://localhost:11434` for local dev; set to `http://ollama:11434` (or equivalent) under the planned k3s/minikube deployment.

Scratch/prototype — role names and the return format may still change as `prompts/` and `write/` firm up. See `../README.md`.
