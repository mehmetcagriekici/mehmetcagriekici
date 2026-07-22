import json
import os

from custom_types.custom_types import Document

# intentionally left out of the matching corpus:
# - profile["personal"] (contact info, not a fit signal)
# - profile["eeo"] (demographic/compliance answers — kept out of a semantic
#   "fit" search so protected-characteristic text can never influence a match score)
# - profile["screening_answers"] (generated per-application, not a stored fact)
# - profile["work_experience"] (currently empty)


def _load_json(path: str):
    with open(path, "r") as f:
        return json.load(f)


def _skill_documents(profile: dict) -> list[Document]:
    documents = []
    for category, skills in profile.get("skills", {}).items():
        for skill in skills:
            fact = {"category": category, "skill": skill}
            documents.append(Document(id=f"skill:{category}:{skill}", content=json.dumps(fact)))
    return documents


def _project_documents(profile: dict, projects_detail: dict) -> list[Document]:
    # merge profile.json's project entry with projects-detail.json's deeper
    # entry for the same project (matched by name) into one atomic fact
    detail_by_name = {p["name"]: p for p in projects_detail.get("projects", [])}
    documents = []
    for project in profile.get("projects", []):
        merged = dict(project)
        detail = detail_by_name.get(project["name"])
        if detail is not None:
            merged["planning_process"] = detail.get("planning_process")
            merged["structure"] = detail.get("structure")
            merged["turning_points"] = detail.get("turning_points")
        documents.append(Document(id=f"project:{project['name']}", content=json.dumps(merged)))
    return documents


def _certification_documents(profile: dict) -> list[Document]:
    return [
        Document(id=f"certification:{c['name']}", content=json.dumps(c))
        for c in profile.get("certifications", [])
    ]


def _education_document(profile: dict) -> list[Document]:
    education = profile.get("education")
    if not education:
        return []
    return [Document(id="education", content=json.dumps(education))]


def _experience_document(profile: dict) -> list[Document]:
    note = profile.get("professional_experience_note")
    if not note:
        return []
    fact = {
        "professional_experience_note": note,
        "years_of_professional_experience": profile.get("years_of_professional_experience"),
    }
    return [Document(id="professional_experience", content=json.dumps(fact))]


def _job_preference_documents(profile: dict) -> list[Document]:
    documents = []
    for key, value in profile.get("job_preferences", {}).items():
        documents.append(Document(id=f"job_preference:{key}", content=json.dumps({key: value})))
    return documents


def _known_gap_documents(known_gaps: dict) -> list[Document]:
    return [
        Document(id=f"known_gap:{gap['gap']}", content=json.dumps(gap))
        for gap in known_gaps.get("known_gaps", [])
    ]


def _general_story_documents(general_stories: dict) -> list[Document]:
    return [
        Document(id=f"story:{story['id']}", content=json.dumps(story))
        for story in general_stories.get("general_stories", [])
    ]


def _preference_documents(preferences: dict) -> list[Document]:
    documents = []
    for key, value in preferences.get("preferences", {}).items():
        documents.append(Document(id=f"preference:{key}", content=json.dumps({key: value})))
    return documents


# one Document per atomic fact, built from the five source_of_truth files
def build_source_of_truth_documents(source_of_truth_dir: str) -> list[Document]:
    profile = _load_json(os.path.join(source_of_truth_dir, "profile.json"))
    projects_detail = _load_json(os.path.join(source_of_truth_dir, "projects-detail.json"))
    known_gaps = _load_json(os.path.join(source_of_truth_dir, "known-gaps.json"))
    general_stories = _load_json(os.path.join(source_of_truth_dir, "general-stories.json"))
    preferences = _load_json(os.path.join(source_of_truth_dir, "preferences.json"))

    documents: list[Document] = []
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


# job postings arrive from sourcing as JSON already, so the query string is
# just that JSON serialized — no per-ATS flattening logic needed
def job_posting_to_query(job_posting: dict) -> str:
    return json.dumps(job_posting)
