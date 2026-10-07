"""Gap-rule cases frozen from the review-and-fix rounds of 2026-10-07.

Every case comes from the commit messages of 29a4495, c1946a2, 6e15723 and
3a07d39, or from the three most recent external reviews -- no new phrasings.
Where the code currently gives the wrong answer, the case is marked xfail
(strict, so a fix that makes it pass is noticed) and listed in BACKLOG.md.
"""

import json
from pathlib import Path

import pytest

from tailoring.gaps.gaps import decide_gaps

KNOWN_GAPS = json.loads(
    (Path(__file__).resolve().parents[1] / "source_of_truth" / "known-gaps.json").read_text(
        encoding="utf-8"
    )
)["known_gaps"]

VISA = "visa_sponsorship_needed"
DEGREE = "in_progress_degree"
EXPERIENCE = "no_professional_experience"


def _decision(posting: dict, gap: str):
    return {d.gap: d for d in decide_gaps(posting, KNOWN_GAPS)}[gap]


def _xfail(reason: str):
    return pytest.mark.xfail(reason=f"{reason}, see BACKLOG.md", strict=True)


CASES = [
    # --- visa: remote roles ---------------------------------------------------
    # 29a4495
    pytest.param(
        {"location": "Remote", "workplace_type": "Remote"},
        VISA,
        False,
        id="remote-plus-remote-mode",
    ),
    pytest.param(
        {"location": "Remote", "description": "We cannot sponsor visas."},
        VISA,
        False,
        id="remote-cannot-sponsor",
    ),
    pytest.param(
        {"location": "Remote", "description": "Must be authorized to work in the United States."},
        VISA,
        True,
        id="remote-authorized-to-work-in-us",
    ),
    # c1946a2
    pytest.param(
        {"location": "Remote - Anywhere in the US"}, VISA, True, id="remote-anywhere-in-us"
    ),
    pytest.param(
        {"location": "Remote (US residents only)"}, VISA, True, id="remote-us-residents-only"
    ),
    # 6e15723 / review 4
    pytest.param({"location": "US - Remote"}, VISA, True, id="region-before-remote-dash"),
    pytest.param(
        {"location": "United States (Remote)"}, VISA, True, id="region-before-remote-parens"
    ),
    pytest.param(
        {"location": "Berlin, Germany(Remote)"}, VISA, True, id="region-before-remote-nospace"
    ),
    pytest.param(
        {"location": "London, UK; Remote"}, VISA, True, id="region-before-remote-semicolon"
    ),
    pytest.param({"location": "Remote - US"}, VISA, True, id="region-after-remote"),
    pytest.param({"location": "Remote (EU timezones)"}, VISA, False, id="remote-eu-timezones"),
    pytest.param({"location": "Remote - worldwide"}, VISA, False, id="remote-worldwide"),
    pytest.param({"location": "Remote-first"}, VISA, False, id="remote-first"),
    pytest.param({"location": "Fully remote"}, VISA, False, id="fully-remote"),
    pytest.param(
        # place name added: the source phrase is "candidates must be based in"
        {"location": "Remote", "description": "Candidates must be based in Canada."},
        VISA,
        True,
        id="remote-candidates-must-be-based-in",
    ),
    pytest.param(
        {"location": "Remote", "description": "Open to candidates in the EU."},
        VISA,
        True,
        id="remote-open-to-candidates-in-eu",
    ),
    pytest.param(
        {"location": "Remote", "description": "US-based candidates only."},
        VISA,
        True,
        id="remote-us-based-candidates",
    ),
    pytest.param(
        {"location": "Remote", "description": "Acme is based in Berlin."},
        VISA,
        False,
        id="remote-company-based-in-berlin",
    ),
    # 3a07d39 / review 5
    pytest.param(
        {"location": "Remote", "description": "Hybrid, 3 days a week in our Berlin office."},
        VISA,
        True,
        id="remote-location-hybrid-description",
    ),
    # --- visa: Turkey -----------------------------------------------------------
    # review 4 / 6e15723
    pytest.param(
        {"location": "Istanbul or Berlin", "workplace_type": "hybrid"},
        VISA,
        True,
        id="istanbul-or-berlin",
    ),
    # review 5 / 3a07d39
    pytest.param({"location": "Istanbul or Remote"}, VISA, False, id="istanbul-or-remote"),
    pytest.param({"location": "Istanbul / Remote"}, VISA, False, id="istanbul-slash-remote"),
    # review 6
    pytest.param(
        {"location": "Istanbul, Turkey", "description": "On-site at our Berlin office."},
        VISA,
        True,
        id="istanbul-location-onsite-berlin",
    ),
    # added with the fix for the case above: an office in Turkey stays exempt
    pytest.param(
        {"location": "Istanbul, Turkey", "description": "On-site at our Istanbul office."},
        VISA,
        False,
        id="istanbul-location-onsite-istanbul",
    ),
    # --- degree -------------------------------------------------------------------
    # c1946a2
    pytest.param(
        {"description": "A Master’s in Computer Science is required."},
        DEGREE,
        True,
        id="masters-curly-apostrophe",
    ),
    pytest.param({"description": "Ph.D. preferred."}, DEGREE, True, id="phd-dotted"),
    # 6e15723 / review 4
    pytest.param({"location": "Boston, MA or Remote"}, DEGREE, False, id="state-code-in-location"),
    # 3a07d39 / review 5
    pytest.param(
        {"description": "High school diploma required."}, DEGREE, False, id="high-school-diploma"
    ),
    pytest.param(
        {"description": "Boston, MA or remote."}, DEGREE, False, id="state-code-in-description"
    ),
    # --- experience ---------------------------------------------------------------
    # 6e15723 / review 4
    pytest.param(
        {"description": "We are 12 years old."}, EXPERIENCE, False, id="company-12-years-old"
    ),
    pytest.param(
        {"description": "Founded 10 years ago."}, EXPERIENCE, False, id="founded-10-years-ago"
    ),
    # 3a07d39 / review 5
    pytest.param(
        {"description": "5+ yrs of Go experience required."},
        EXPERIENCE,
        True,
        id="yrs-abbreviation",
    ),
    pytest.param(
        {"title": "Backend Engineer (5+ years)", "description": "Build APIs."},
        EXPERIENCE,
        True,
        id="years-in-title",
    ),
    pytest.param(
        {"description": "Acme celebrates 25 years of innovation."},
        EXPERIENCE,
        True,
        id="company-history-still-raises",
    ),
    # review 6
    pytest.param(
        {"description": "Minimum 18 months of experience with Go."},
        EXPERIENCE,
        True,
        id="months-of-experience",
    ),
]


@pytest.mark.parametrize(("posting", "gap", "expected"), CASES)
def test_gap_applies(posting: dict, gap: str, expected: bool) -> None:
    assert _decision(posting, gap).applies is expected


# 3a07d39 / review 5: company-history years lines still raise the experience
# gap, but are never quoted to the model as the candidate's requirement.
@pytest.mark.parametrize(
    "line",
    [
        pytest.param("Acme celebrates 25 years of innovation.", id="25-years-of-innovation"),
        pytest.param("With over 20 years in the industry, we lead.", id="20-years-in-the-industry"),
    ],
)
def test_company_history_not_quoted(line: str) -> None:
    decision = _decision({"description": line}, EXPERIENCE)
    assert decision.applies is True
    assert decision.requirements == []
