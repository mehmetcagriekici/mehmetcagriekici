from datetime import datetime
from enum import Enum
from typing import Literal, TypedDict


class GreenhousePosting(TypedDict):
    id: str
    company_name: str
    title: str
    location: dict[Literal["name"], str]
    content: str
    absolute_url: str
    first_published: str
    internal_job_id: int


class Posting(TypedDict):
    id: str | None
    ats: str | None
    board: str | None
    company: str | None
    title: str | None
    location: str | None
    employment_type: str | None
    workplace_type: Literal["remote", "hybrid", "onsite", "unknown"]
    description: str | None
    url: str | None
    posted_at: datetime | None
    requisition_key: str | None
    raw: GreenhousePosting


class SkipReason(Enum):
    FETCH_FAILED = "FETCH_FAILED"
    MISSING_KEY = "MISSING_KEY"
    MISSING_FIELD = "MISSING_FIELD"
    STALE = "STALE"


class Skip(TypedDict):
    what: str
    reason: SkipReason
    detail: str
