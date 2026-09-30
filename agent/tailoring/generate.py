import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from pypdf.errors import PyPdfError

from tailoring.gaps.gaps import GapDecision, decide_gaps
from tailoring.llm.client import OllamaError, llm_ollama
from tailoring.prompts.application import build_application_prompt
from tailoring.prompts.cover_letter import build_cover_letter_prompt
from tailoring.prompts.resume import build_resume_prompt
from tailoring.prompts.system_prompt import SYSTEM_PROMPT
from tailoring.write.write import (
    RESUME_JSON_SCHEMA,
    ParseResult,
    WriteError,
    WriteResult,
    application_answers_schema,
    cover_letter_schema,
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
    # every known gap's applies/doesn't-apply decision and why (gaps/gaps.py),
    # for the review email and review_gate/ -- set before any LLM call
    gap_decisions: list[GapDecision] = field(default_factory=list)


# A broken LLM response has no content to show anyone, and there are no
# retries (see write/README.md) -- so the application is dead, and spending
# the single Ollama slot on its remaining calls would only delay every other
# posting queued behind it. OVERFLOW is deliberately not here: that content is
# real and goes to the user for approve/reject, so generation continues.
_BROKEN_RESPONSE = (WriteError.INVALID_JSON, WriteError.VALIDATION_ERROR)


# Facts the gap rules govern, kept out of the resume and cover letter prompts
# even when search ranks them: known_gap:* (the cover letter gets the gaps that
# apply in their own block), education (holds the GPA and degree status),
# professional_experience (the experience gap), and job_preference:* (screening
# answers like visa and salary, answered deterministically, never in prose).
# Otherwise a fact search happened to return could put a gap the posting never
# asked about straight back into the letter. The application call keeps all
# facts -- a free-text answer about experience or education must stay honest.
_GAP_GOVERNED_PREFIXES = ("known_gap:", "job_preference:")
_GAP_GOVERNED_IDS = ("education", "professional_experience")


def _writing_facts(facts: list[dict]) -> list[dict]:
    return [
        f
        for f in facts
        if not f["doc_id"].startswith(_GAP_GOVERNED_PREFIXES)
        and f["doc_id"] not in _GAP_GOVERNED_IDS
    ]


# Job posting IDs come from outside (ATS data), so they're reduced to a safe
# filename stem before touching the filesystem -- an ID containing "/" or ".."
# must not be able to escape output_dir. tracking/ (not yet built) keys its
# per-application files by the same ID and should reuse this, so two IDs that
# differ only in special characters map to the same file in both places.
def filename_stem(posting_id: object) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", str(posting_id))
    if not stem.strip("_"):
        raise ValueError(f"job posting id {posting_id!r} has no usable filename characters")
    return stem


async def generate(
    facts: list[dict],
    job_posting: dict,
    personal: dict,
    questions: list[dict],
    known_gaps: list[dict],
    output_dir: str,
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

    # known_gaps is known-gaps.json's full list, independent of hybrid_search's
    # ranking (option (b), ../CLAUDE.md). Empty means the caller didn't load it
    # -- every gap would silently count as "doesn't apply".
    if not known_gaps:
        raise ValueError("generate: known_gaps is empty -- load known-gaps.json")
    # Which gaps the cover letter raises is decided here, in code, before any
    # LLM call: only the ones the posting actually asks about.
    result.gap_decisions = decide_gaps(job_posting, known_gaps)
    gaps_to_raise = [d for d in result.gap_decisions if d.applies]
    writing_facts = _writing_facts(facts)

    # Per-application filenames, keyed by job posting ID (same convention
    # tracking/ already uses for its own per-application JSON files -- see
    # ../CLAUDE.md's tracking/ section). Without this, every call to generate()
    # would write to the same "resume.pdf"/"cover_letter.pdf", silently
    # overwriting whatever the previous posting produced. A missing "id" is a
    # malformed job_posting -- let the KeyError propagate rather than papering
    # over it with a fallback name. output_dir is required so files never land
    # in whatever directory the process happens to run from.
    stem = filename_stem(job_posting["id"])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    resume_path = str(out / f"{stem}_resume.pdf")
    cover_letter_path = str(out / f"{stem}_cover_letter.pdf")

    # generate resume
    resume_prompt = build_resume_prompt(writing_facts, job_posting)
    try:
        resume_response = await llm_ollama(resume_prompt, SYSTEM_PROMPT, RESUME_JSON_SCHEMA)
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
    if result.resume.error in _BROKEN_RESPONSE:
        return result

    # generate cover letter
    cover_letter_prompt = build_cover_letter_prompt(writing_facts, job_posting, gaps_to_raise)
    try:
        cover_letter_response = await llm_ollama(
            cover_letter_prompt, SYSTEM_PROMPT, cover_letter_schema(bool(gaps_to_raise))
        )
    except OllamaError:
        logger.exception("generate: cover letter LLM call failed")
        result.cover_letter = WriteResult(path=None, error=WriteError.LLM_FAILURE)
        return result
    try:
        result.cover_letter = await write_cover_letter(
            cover_letter_response,
            personal,
            output_path=cover_letter_path,
            gaps_expected=bool(gaps_to_raise),
            company=job_posting.get("company"),
        )
    except (PlaywrightError, PyPdfError):
        logger.exception("generate: rendering the cover letter failed")
        result.cover_letter = WriteResult(path=None, error=WriteError.RENDER_FAILURE)
        return result
    if result.cover_letter.error in _BROKEN_RESPONSE:
        return result

    # generate form answers
    application_prompt = build_application_prompt(facts, job_posting, questions)
    try:
        application_response = await llm_ollama(
            application_prompt, SYSTEM_PROMPT, application_answers_schema(questions)
        )
    except OllamaError:
        logger.exception("generate: application LLM call failed")
        result.application = ParseResult(answers=None, error=WriteError.LLM_FAILURE)
        return result
    # parse_application_answers is sync -- no rendering, so no Playwright/pypdf
    # failure mode to catch here the way write_resume/write_cover_letter have.
    result.application = parse_application_answers(application_response, questions)

    return result
