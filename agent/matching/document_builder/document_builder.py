import json
import logging
import os

from matching.custom_types.custom_types import Document

logger = logging.getLogger(__name__)

# intentionally left out of the matching corpus:
# - profile["personal"] (contact info, not a fit signal)
# - profile["eeo"] (demographic/compliance answers — kept out of a semantic
#   "fit" search so protected-characteristic text can never influence a match score)
# - profile["screening_answers"] (generated per-application, not a stored fact)
# - profile["work_experience"] (currently empty)


# ensure_ascii=False keeps non-ASCII text as-is ("München", "Açıköğretim")
# instead of \u escapes, which split words for BM25 and read as noise to the
# embedding model
def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# the candidate's own hand-written summary -- a fit statement in their words
def _summary_document(profile: dict) -> list[Document]:
    summary = profile.get("summary")
    if not summary:
        return []
    return [Document(id="summary", content=_dumps({"summary": summary}))]


def _skill_documents(profile: dict) -> list[Document]:
    documents = []
    for category, skills in profile.get("skills", {}).items():
        for skill in skills:
            fact = {"category": category, "skill": skill}
            documents.append(Document(id=f"skill:{category}:{skill}", content=_dumps(fact)))
    return documents


def _project_documents(profile: dict, projects_detail: dict) -> list[Document]:
    # merge profile.json's project entry with projects-detail.json's deeper
    # entry for the same project (matched by name) into one atomic fact
    detail_by_name = {p["name"]: p for p in projects_detail.get("projects", [])}
    documents = []
    for project in profile.get("projects", []):
        merged = dict(project)
        detail = detail_by_name.get(project["name"])
        if detail is None:
            # still indexed, just without incident-level material -- usually a
            # new project not yet written up in projects-detail.json, or a name
            # that differs slightly between the two files
            logger.warning(
                "document_builder: no projects-detail.json entry for project %r",
                project["name"],
            )
        else:
            merged["planning_process"] = detail.get("planning_process")
            merged["structure"] = detail.get("structure")
            merged["turning_points"] = detail.get("turning_points")
        documents.append(Document(id=f"project:{project['name']}", content=_dumps(merged)))
    return documents


def _certification_documents(profile: dict) -> list[Document]:
    return [
        Document(id=f"certification:{c['name']}", content=_dumps(c))
        for c in profile.get("certifications", [])
    ]


def _education_document(profile: dict) -> list[Document]:
    education = profile.get("education")
    if not education:
        return []
    return [Document(id="education", content=_dumps(education))]


def _experience_document(profile: dict) -> list[Document]:
    note = profile.get("professional_experience_note")
    if not note:
        return []
    fact = {
        "professional_experience_note": note,
        "years_of_professional_experience": profile.get("years_of_professional_experience"),
    }
    return [Document(id="professional_experience", content=_dumps(fact))]


def _job_preference_documents(profile: dict) -> list[Document]:
    documents = []
    for key, value in profile.get("job_preferences", {}).items():
        documents.append(Document(id=f"job_preference:{key}", content=_dumps({key: value})))
    return documents


def _known_gap_documents(known_gaps: dict) -> list[Document]:
    return [
        Document(id=f"known_gap:{gap['gap']}", content=_dumps(gap))
        for gap in known_gaps.get("known_gaps", [])
    ]


def _general_story_documents(general_stories: dict) -> list[Document]:
    return [
        Document(id=f"story:{story['id']}", content=_dumps(story))
        for story in general_stories.get("general_stories", [])
    ]


def _preference_documents(preferences: dict) -> list[Document]:
    documents = []
    for key, value in preferences.get("preferences", {}).items():
        documents.append(Document(id=f"preference:{key}", content=_dumps({key: value})))
    return documents


# one Document per atomic fact, built from the five source_of_truth files
def build_source_of_truth_documents(source_of_truth_dir: str) -> list[Document]:
    profile = _load_json(os.path.join(source_of_truth_dir, "profile.json"))
    projects_detail = _load_json(os.path.join(source_of_truth_dir, "projects-detail.json"))
    known_gaps = _load_json(os.path.join(source_of_truth_dir, "known-gaps.json"))
    general_stories = _load_json(os.path.join(source_of_truth_dir, "general-stories.json"))
    preferences = _load_json(os.path.join(source_of_truth_dir, "preferences.json"))

    documents: list[Document] = []
    documents += _summary_document(profile)
    documents += _skill_documents(profile)
    documents += _project_documents(profile, projects_detail)
    documents += _certification_documents(profile)
    documents += _education_document(profile)
    documents += _experience_document(profile)
    documents += _job_preference_documents(profile)
    documents += _known_gap_documents(known_gaps)
    documents += _general_story_documents(general_stories)
    documents += _preference_documents(preferences)
    return documents


# The posting fields that carry content. Everything that reads a posting's text
# -- the search query here, tailoring's prompts and gap rules -- goes through
# posting_content(), so bookkeeping fields (id, ats, board, url, posted_at,
# salary) and the stored raw ATS response never leak into a query, a prompt, or
# a keyword rule (dumping the whole dict would have sent `raw` -- a second copy
# of the description plus ATS metadata -- everywhere, and calibrated the
# threshold against a different query than production sends). requirements/
# nice_to_have exist only on the synthetic fixtures; normalized postings carry
# everything in description.
POSTING_CONTENT_FIELDS = (
    "title",
    "company",
    "location",
    "workplace_type",
    "employment_type",
    "description",
    "requirements",
    "nice_to_have",
)


def posting_content(job_posting: dict) -> dict:
    return {
        field: job_posting[field]
        for field in POSTING_CONTENT_FIELDS
        if job_posting.get(field) not in (None, "", [])
    }


# the query string is the posting's content fields serialized as JSON — no
# per-ATS flattening logic needed, since sourcing normalizes every ATS
def job_posting_to_query(job_posting: dict) -> str:
    return _dumps(posting_content(job_posting))
