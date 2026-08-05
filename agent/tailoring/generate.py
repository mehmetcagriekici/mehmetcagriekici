import logging
from dataclasses import dataclass

from playwright.async_api import Error as PlaywrightError
from pypdf.errors import PyPdfError

from tailoring.llm.client import OllamaError, llm_ollama
from tailoring.prompts.application import build_application_prompt
from tailoring.prompts.cover_letter import build_cover_letter_prompt
from tailoring.prompts.resume import build_resume_prompt
from tailoring.prompts.system_prompt import SYSTEM_PROMPT
from tailoring.write.write import (
    ParseResult,
    WriteError,
    WriteResult,
    parse_application_answers,
    write_cover_letter,
    write_resume,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerateResult:
    # None means that step was never reached (aborted earlier, or the LLM
    # call itself failed) -- a WriteResult/ParseResult with .error set means
    # it was reached and failed. See write/README.md's WriteError note.
    resume: WriteResult | None = None
    cover_letter: WriteResult | None = None
    application: ParseResult | None = None


async def generate(
    facts: list[dict], job_posting: dict, personal: dict, questions: list[dict]
) -> GenerateResult:
    # No implicit None-checks: llm_ollama raises OllamaError instead of
    # returning None on failure (see llm/client.py), and write_resume/
    # write_cover_letter raise playwright.async_api.Error/pypdf.errors.PyPdfError
    # for the failure modes they don't fully resolve into a WriteResult
    # themselves (bad JSON/failed validation/overflow do; a Chromium crash or an
    # unreadable output PDF don't). Both are caught here, explicitly, and turned
    # into the matching WriteError. Anything else is a genuine bug and is left
    # to propagate rather than being caught and hidden.
    result = GenerateResult()

    # Per-application filenames, keyed by job posting ID (same convention
    # tracking/ already uses for its own per-application JSON files -- see
    # ../CLAUDE.md's tracking/ section). Without this, every call to generate()
    # would write to the same "resume.pdf"/"cover_letter.pdf", silently
    # overwriting whatever the previous posting produced. A missing "id" is a
    # malformed job_posting -- let the KeyError propagate rather than papering
    # over it with a fallback name.
    resume_path = f"{job_posting['id']}_resume.pdf"
    cover_letter_path = f"{job_posting['id']}_cover_letter.pdf"

    # generate resume
    resume_prompt = build_resume_prompt(facts, job_posting)
    try:
        resume_response = await llm_ollama(resume_prompt, SYSTEM_PROMPT)
    except OllamaError:
        logger.exception("generate: resume LLM call failed")
        result.resume = WriteResult(path=None, error=WriteError.LLM_FAILURE)
        return result
    try:
        result.resume = await write_resume(resume_response, personal, resume_path)
    except (PlaywrightError, PyPdfError):
        logger.exception("generate: rendering the resume failed")
        result.resume = WriteResult(path=None, error=WriteError.RENDER_FAILURE)
        return result

    # generate cover letter
    cover_letter_prompt = build_cover_letter_prompt(facts, job_posting)
    try:
        cover_letter_response = await llm_ollama(cover_letter_prompt, SYSTEM_PROMPT)
    except OllamaError:
        logger.exception("generate: cover letter LLM call failed")
        result.cover_letter = WriteResult(path=None, error=WriteError.LLM_FAILURE)
        return result
    try:
        result.cover_letter = await write_cover_letter(
            cover_letter_response,
            personal,
            company=job_posting.get("company"),
            output_path=cover_letter_path,
        )
    except (PlaywrightError, PyPdfError):
        logger.exception("generate: rendering the cover letter failed")
        result.cover_letter = WriteResult(path=None, error=WriteError.RENDER_FAILURE)
        return result

    # generate form answers
    application_prompt = build_application_prompt(facts, job_posting, questions)
    try:
        application_response = await llm_ollama(application_prompt, SYSTEM_PROMPT)
    except OllamaError:
        logger.exception("generate: application LLM call failed")
        result.application = ParseResult(answers=None, error=WriteError.LLM_FAILURE)
        return result
    # parse_application_answers is sync -- no rendering, so no Playwright/pypdf
    # failure mode to catch here the way write_resume/write_cover_letter have.
    result.application = parse_application_answers(application_response)

    return result
