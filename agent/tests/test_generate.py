"""generate()'s prompt-size handling (BACKLOG FIX NOW, 2026-10-07): facts are
trimmed from the lowest-ranked end until the prompt fits, instead of failing
with PROMPT_TOO_LONG -- which would permanently exclude the best matches."""

from tailoring.generate import fit_facts
from tailoring.llm.client import prompt_fits
from tailoring.prompts.system_prompt import SYSTEM_PROMPT


def _build(facts: list[dict]) -> str:
    return "\n".join(f["content"] for f in facts)


def test_fit_facts_drops_lowest_ranked_until_it_fits() -> None:
    facts = [{"doc_id": f"project:{i}", "content": "x" * 6000} for i in range(10)]
    assert not prompt_fits(SYSTEM_PROMPT, _build(facts))

    kept = fit_facts(_build, facts)

    assert prompt_fits(SYSTEM_PROMPT, _build(kept))
    assert 0 < len(kept) < len(facts)
    assert kept == facts[: len(kept)]  # best-ranked facts kept, in order


def test_fit_facts_keeps_everything_when_it_fits() -> None:
    facts = [{"doc_id": "skill:go", "content": "Go"}]
    assert fit_facts(_build, facts) == facts
