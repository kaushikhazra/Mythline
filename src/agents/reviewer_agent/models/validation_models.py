from pydantic import BaseModel


class ValidationResult(BaseModel):
    valid: bool
    error: str
    suggestion: str
