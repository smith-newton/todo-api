from datetime import datetime
from pydantic import BaseModel, Field

class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    completed: bool = False
    due_date: datetime | None = None

class TodoUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    completed: bool
    due_date: datetime | None = None
