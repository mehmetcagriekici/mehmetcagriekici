import re
from dataclasses import dataclass, field

from matching.document_builder.document_builder import posting_content

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


def _flatten(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(_flatten(v) for v in value)
    return ""


# Curly quotes are normalized once here, so every rule's regex can assume a
# straight apostrophe -- real ATS HTML is full of them ("Master’s" slipped past
# the degree rule).
def _normalize(text: str) -> str:
    return text.replace("\u2019", "'").replace("\u2018", "'")


# every string in the posting's content fields (posting_content -- never ids,
# urls, or the stored raw ATS response), flattened; `without` drops fields a
# rule must not read
def _posting_text(job_posting: dict, without: tuple[str, ...] = ()) -> str:
    content = {k: v for k, v in posting_content(job_posting).items() if k not in without}
    return _normalize(_flatten(content))


# The lines the years rule checks: every line of the description -- sourcing
# puts each HTML bullet on its own line, and a prose line is further split into
# sentences -- plus the requirements/nice_to_have lists the synthetic fixtures
# carry. Scanning only requirements went silent on normalized postings, which
# have no such list: a description's "3+ years ..." raised nothing.
def _candidate_lines(job_posting: dict) -> list[str]:
    lines = []
    for key in ("requirements", "nice_to_have"):
        lines += [line for line in job_posting.get(key) or [] if isinstance(line, str)]
    for line in str(job_posting.get("description") or "").splitlines():
        lines += re.split(r"(?<=[.!?])\s+", line)
    return [_normalize(line.strip()) for line in lines if line.strip()]


def _first_match(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


# "3+ years", "5-7 years", "2 years", and spelled out: "two years" -- counted
# only when shaped like a requirement: "years" followed by a requirement word
# ("3+ years of Go", "5 years building", "years' experience"), or a line that
# also says "experience". "We are 12 years old" / "founded 10 years ago" don't
# count -- they'd otherwise be quoted to the model as the posting's requirement.
_YEARS = r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:\+|-\s*\d+)?\s*years?\b"
_YEARS_REQUIREMENT = re.compile(
    _YEARS + r"'?\s*(?:of|in|with|experience|building|working|developing|designing|writing"
    r"|professional|hands-on|industry|commercial)\b",
    re.I,
)
_YEARS_ANY = re.compile(_YEARS, re.I)


def _is_years_requirement(line: str) -> bool:
    return bool(
        _YEARS_REQUIREMENT.search(line)
        or (_YEARS_ANY.search(line) and re.search(r"\bexperience\b", line, re.I))
    )


_PROFESSIONAL_EXPERIENCE = re.compile(
    r"\b(?:professional|work|industry|commercial|paid)\s+experience\b", re.I
)


def _no_professional_experience(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    years_lines = [line for line in _candidate_lines(job_posting) if _is_years_requirement(line)]
    if years_lines:
        return True, f"posting asks for years of experience: {years_lines[0]!r}", years_lines
    phrase = _first_match(_PROFESSIONAL_EXPERIENCE, text)
    if phrase:
        return True, f"posting asks for {phrase!r}", []
    return False, "posting doesn't ask for years of or professional experience", []


_DEGREE = re.compile(
    r"\b(?:degree|bachelor'?s?|master'?s|b\.?sc|m\.?sc|bs/ms|ba/bs|diploma|ph\.?\s?d)\b"
    # Short forms (BS, M.S., BA, MA) only in degree context -- followed by "in",
    # "degree", "or", or a slash -- and case-sensitive, so lowercase "ms"/"ma"
    # never match. (State codes like "Boston, MA" are kept out by not reading
    # the location field at all, see _in_progress_degree.)
    r"|(?-i:\b(?:B\.?S|M\.?S|B\.?A|M\.?A)\.?)(?=\s+(?:in|degree|or)\b|/)",
    re.I,
)


def _in_progress_degree(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    # location excluded: a degree requirement never appears there, but US state
    # codes do ("Boston, MA or Remote" read as a degree before)
    word = _first_match(_DEGREE, _posting_text(job_posting, without=("location",)))
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
# Words in a remote qualifier that only constrain working hours or say "no
# restriction" -- including a region named as a timezone ("EU timezones").
# They're removed from the qualifier, and the role counts as region-restricted
# if any word is left: "Anywhere in the US" leaves "in the US". (Checking only
# whether such a word was *present* let "Anywhere in the US" pass as fully
# remote -- the unsafe direction.)
_HOURS_OR_UNRESTRICTED = re.compile(
    r"[\w/+-]*\s*\btime ?zones?\b|\b(?:utc|gmt)(?:\s*[+-]\s*\d+)?\b"
    r"|\b(?:cet|cest|est|edt|pst|pdt)\b|\bworldwide\b|\banywhere\b|\bglobal(?:ly)?\b"
    r"|\bteam\b|\bfriendly\b|\bfirst\b|\bfully\b|\bonly\b|\bhours?\b|\boverlap\b",
    re.I,
)
# Work authorization or residence required *of the candidate*, tied to a place:
# "authorized to work in the United States", "eligible to work in the EU",
# "candidates must be based in Canada", "you must reside in Germany". On a
# fully remote role this is what matters -- a bare "we cannot sponsor visas"
# doesn't, since working remotely from Turkey needs no visa. Only
# candidate-directed phrasings count: a company blurb's "Acme is based in
# Berlin" appears in most postings and says nothing about where you must live.
# The place is capitalized words on the same line (keywords are matched
# case-insensitively).
_PLACE = r"(?P<place>[A-Z][\w-]*(?:\.[A-Z][\w-]*)*\.?(?:[ \t]+[A-Z][\w-]*(?:\.[A-Z][\w-]*)*\.?)*)"
_PLACE_BOUND_AUTHORIZATION = (
    re.compile(
        r"(?i:\b(?:authori[sz]ed|eligib(?:le|ility)|right)\s+to\s+work\s+in\s+(?:the\s+)?)" + _PLACE
    ),
    re.compile(
        r"(?i:\b(?:must|should|need\s+to|required\s+to)\s+(?:be\s+)?"
        r"(?:based|located|resid(?:e|ing|ent)|liv(?:e|ing))\s+in\s+(?:the\s+)?)" + _PLACE
    ),
    # "open to candidates in the EU", "applicants located in Canada"
    re.compile(
        r"(?i:\b(?:candidates|applicants)\s+(?:(?:based|located|residing)\s+)?in\s+(?:the\s+)?)"
        + _PLACE
    ),
    # "US-based candidates only", "EU-based applicants"
    re.compile(r"\b(?P<place>[A-Z][A-Za-z.]*)-based\s+(?i:candidates|applicants|residents)\b"),
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


# the structured work mode (the normalized posting's workplace_type, real for
# Lever/Ashby) -- None means only location text is available
def _workplace_mode(job_posting: dict) -> str | None:
    return _WORKPLACE_MODES.get(str(job_posting.get("workplace_type") or "").strip().lower())


def _visa_sponsorship_needed(job_posting: dict, text: str) -> tuple[bool, str, list[str]]:
    # location text and the structured work mode are read separately -- joined
    # into one string, a second "remote" after "Remote" was once mistaken for a
    # region qualifier
    location = str(job_posting.get("location") or "").strip()
    mode = _workplace_mode(job_posting)

    # Turkey exempts the gap only when it's the sole location -- "Istanbul or
    # Berlin" may well mean Berlin
    if _TURKEY.search(location) and not re.search(r"\bor\b|/|;|\|", location):
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

    # Remote. "Remote (US/Canada)", "US - Remote", "United States (Remote)" --
    # or a remote work mode with location "United States" -- still require
    # living/being authorized there; "Remote (EU timezones)" only constrains
    # hours. So the word "remote" is removed and whatever is left, on either
    # side, is the qualifier. (Reading only the text after "Remote" missed
    # every region written before it.)
    qualifier = _REMOTE.sub(" ", location)
    if re.search(r"[^\W\d_]{2,}", _HOURS_OR_UNRESTRICTED.sub(" ", qualifier)):
        return True, f"remote, but restricted to a region: {location!r}", []

    matches = (m for pattern in _PLACE_BOUND_AUTHORIZATION for m in pattern.finditer(text))
    for match in matches:
        place = match.group("place")
        if not _TURKEY.search(place):
            required = match.group(0).strip().rstrip(".")
            return True, f"remote, but posting requires {required!r}", []

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
