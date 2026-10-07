from pydantic import BaseModel


# shared search shape for job_posting and source_of_truth entries
class Document(BaseModel):
    id: str
    content: str
