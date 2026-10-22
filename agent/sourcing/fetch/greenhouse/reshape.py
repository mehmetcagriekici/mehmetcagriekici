import html
from datetime import datetime

from sourcing.custom_types.posting import GreenhousePosting, Posting


def reshape(board: str, jobs: list[GreenhousePosting]) -> list[Posting]:
    new_jobs = []
    for job in jobs:
        requisition_key = str(job['internal_job_id']) if job.get('internal_job_id') else None
        content = job.get('content')
        description = html.unescape(content) if content is not None else None
        new_job = Posting(id=f"greenhouse:{board}:{job['id']}" if job.get('id') else None,
                          ats='greenhouse',
                          board=board,
                          company=job.get('company_name'),
                          title=job.get('title'),
                          location=job.get('location_name'),
                          employment_type=None,
                          workplace_type='unknown',
                          description=description,
                          url=job.get('absolute_url'),
                          posted_at=parse_time(job.get('first_published')),
                          requisition_key=requisition_key,
                          raw=job.get('raw'))
        new_jobs.append(new_job)
    return new_jobs


def parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
