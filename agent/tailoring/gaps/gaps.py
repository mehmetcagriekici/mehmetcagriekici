import re
from dataclasses import dataclass, field

# Which known gaps a cover letter raises is decided here, in plain code,
# before the LLM runs -- a gap is raised only if the posting asks for the
# thing it's missing (decided 2026-09-30, see ../../CLAUDE.md). The 7B model
# misapplied these rules about half the time when left to decide them itself
# (visa raised for a remote role, GPA volunteered unasked); keyword rules over
# the posting text are cruder but deterministic, and ambiguity resolves
# toward raising a gap, never hiding one.


@dataclass
class GapDecision:
    gap: str
    applies: bool
    # which rule fired and on what text -- for the review email / review_gate/
    reason: str
    # the gap's fact and the phrasing to hand the LLM (a gap with situational
    # phrasings, like visa sponsorship, has the matching one selected here)
    fact: str
    phrasing: str | None = None
    # posting requirements the paragraph must address verbatim, e.g. "3+ years
    # building web applications with TypeScript" -- so the narrower,
    # stack-specific gap gets named, not just the general one
    requirements: list[str] = field(default_factory=list)


def _posting_text(value: object) -> str:
    # every string in the posting (title, description, requirements, ...),
    # flattened -- numbers like salary figures are irrelevant to these rules
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_posting_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(_posting_text(v) for v in value)
    return ""


def _requirement_lines(job_posting: dict) -> list[str]:
    lines = []
    for key in ("requirements", "nice_to_have"):
        lines += [line for line in job_posting.get(key) or [] if isinstance(line, str)]
    return lines


def _first_match(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


# "3+ years", "5-7 years", "2 years"
_YEARS = re.compile(r"\b\d+\s*(?:\+|-\s*\d+)?\s*years?\b", re.I)
_PROFESSIONAL_EXPERIENCE = re.compile(
    r"\b(?:professional|work|industry|commercial|paid)\s+experience\b", re.I
)


def _no_professional_experience(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    years_lines = [line for line in _requirement_lines(job_posting) if _YEARS.search(line)]
    if years_lines:
        return True, f"posting asks for years of experience: {years_lines[0]!r}", years_lines
    phrase = _first_match(_PROFESSIONAL_EXPERIENCE, text)
    if phrase:
        return True, f"posting asks for {phrase!r}", []
    return False, "posting doesn't ask for years of or professional experience", []


_DEGREE = re.compile(
    r"\b(?:degree|bachelor'?s?|master'?s|b\.?sc|m\.?sc|bs/ms|ba/bs|diploma|phd)\b", re.I
)


def _in_progress_degree(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    word = _first_match(_DEGREE, text)
    if word:
        return True, f"posting mentions {word!r}", []
    return False, "posting doesn't ask for a degree", []


_GPA = re.compile(r"\bgpa\b|\bgrade point average\b", re.I)


def _gpa(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    word = _first_match(_GPA, text)
    if word:
        return True, f"posting asks for {word!r}", []
    return False, "posting doesn't ask for a GPA", []


_TURKEY = re.compile(r"\b(?:turkey|türkiye|turkiye|ankara|istanbul|i̇stanbul|izmir)\b", re.I)
_REMOTE = re.compile(r"\bremote\b", re.I)
_NOT_FULLY_REMOTE = re.compile(
    r"\bno remote\b|\bnot remote\b|\bnon-remote\b|\bon-?site\b|\bhybrid\b|"
    r"\bin[- ]office\b|\boffice-based\b|\bfield-based\b",
    re.I,
)
# a remote qualifier that only constrains working hours, not where you live
_TIMEZONE_ONLY = re.compile(
    r"\btime ?zones?\b|\butc\b|\bgmt\b|\bcet\b|\bworldwide\b|\banywhere\b|\bglobal\b", re.I
)
# work authorization or residence tied to a place -- "authorized to work in the
# US", "eligible to work in the EU", "must reside in Canada". On a fully remote
# role this is what matters; a bare "we cannot sponsor visas" doesn't, since
# working remotely from Turkey needs no visa. The place must start with a
# capital letter (keywords are matched case-insensitively). "based in Berlin"
# describing the company's office also matches -- raising there is the safe
# direction.
_PLACE_BOUND_AUTHORIZATION = re.compile(
    r"(?i:\b(?:authori[sz]ed|eligib(?:le|ility)|right|permitted|reside|residing|resident"
    r"|located|based|live|living)\b)[^.\n]{0,40}?(?i:\bin\s+(?:the\s+)?)"
    r"(?P<place>[A-Z][\w.-]*(?:\s+[A-Z][\w.-]*)*)"
)
_WORKPLACE_MODES = {
    "remote": "remote",
    "hybrid": "hybrid",
    "onsite": "onsite",
    "on-site": "onsite",
    "on site": "onsite",
    "in-office": "onsite",
    "office": "onsite",
}


# the structured work mode, if sourcing provided one (workplace_type from
# Lever/Ashby, or a boolean "remote" flag) -- None means only location text
def _workplace_mode(job_posting: dict) -> str | None:
    mode = _WORKPLACE_MODES.get(str(job_posting.get("workplace_type") or "").strip().lower())
    if mode is None and job_posting.get("remote") is True:
        return "remote"
    return mode


def _visa_sponsorship_needed(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    # location text and the structured work mode are read separately -- joined
    # into one string, a second "remote" (or a "True" flag) after "Remote" was
    # mistaken for a region qualifier
    location = str(job_posting.get("location") or "").strip()
    mode = _workplace_mode(job_posting)

    if _TURKEY.search(location):
        return False, f"role is located in Turkey: {location!r}", []

    if mode in ("hybrid", "onsite"):
        return True, f"workplace type is {mode}: {location!r}", []
    if _NOT_FULLY_REMOTE.search(location):
        return True, f"not a fully remote role: {location!r}", []
    remote_in_location = _REMOTE.search(location)
    if mode != "remote" and not remote_in_location:
        # no remote signal at all (or no usable location) -- ambiguity
        # resolves toward raising the gap
        return True, f"not a fully remote role: {location!r}", []

    # Remote. "Remote (US/Canada)" -- or a remote work mode with location
    # "United States" -- still requires living/being authorized there;
    # "Remote (EU timezones)" only constrains hours.
    qualifier = location[remote_in_location.end() :] if remote_in_location else location
    qualifier = qualifier.strip(" -–—,()")
    if qualifier and not _TIMEZONE_ONLY.search(qualifier):
        return True, f"remote, but restricted to a region: {location!r}", []

    for match in _PLACE_BOUND_AUTHORIZATION.finditer(text):
        if not _TURKEY.search(match.group("place")):
            return True, f"remote, but posting requires {match.group(0).strip()!r}", []

    return False, f"fully remote role: {location or mode!r}", []


# one rule per known-gaps.json id. A gap with no rule here is an error, not a
# silent skip: known-gaps.json is hand-maintained, and a new gap needs its
# "when does the posting ask for this?" rule written before it can be used.
_RULES = {
    "no_professional_experience": _no_professional_experience,
    "in_progress_degree": _in_progress_degree,
    "gpa": _gpa,
    "visa_sponsorship_needed": _visa_sponsorship_needed,
}


def _select_phrasing(gap: dict) -> str:
    phrasing = gap["phrasing"]
    if isinstance(phrasing, str):
        return phrasing
    # situational phrasings: only visa sponsorship has them today, and it only
    # applies in the on-site/relocation situation (fully remote -> not raised)
    if gap["gap"] == "visa_sponsorship_needed":
        return phrasing["onsite_or_relocation"]
    raise ValueError(f"gap {gap['gap']!r} has situational phrasings but no rule to pick one")


def decide_gaps(job_posting: dict, known_gaps: list[dict]) -> list[GapDecision]:
    text = _posting_text(job_posting)
    decisions = []
    for gap in known_gaps:
        rule = _RULES.get(gap["gap"])
        if rule is None:
            raise ValueError(
                f"known gap {gap['gap']!r} has no applicability rule in tailoring/gaps/gaps.py"
            )
        applies, reason, requirements = rule(job_posting, text)
        decisions.append(
            GapDecision(
                gap=gap["gap"],
                applies=applies,
                reason=reason,
                fact=gap["fact"],
                phrasing=_select_phrasing(gap) if applies else None,
                requirements=requirements,
            )
        )
    return decisions
