from pydantic import BaseModel

class MigrationTask(BaseModel):
    """
    Data Transfer Object representing a single code migration task.
    """
    file_path: str
    rule_id: str
    original_code: str
    start_byte: int
    end_byte: int
    llm_suggested_code: str | None = None
