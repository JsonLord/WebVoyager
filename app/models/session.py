from pydantic import BaseModel
from typing import Optional

class SessionResponse(BaseModel):
    session_id: str
    status: str

class TaskRequest(BaseModel):
    task: str

class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    query: Optional[str] = None
    schema_dict: Optional[dict] = None
