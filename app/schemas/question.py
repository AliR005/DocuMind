from pydantic import BaseModel, ConfigDict, field_validator


class QuestionRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Question must not be empty")
        return normalized


class QuestionResponse(BaseModel):
    answer: str
    source_filename: str
    relevance_score: float

    model_config = ConfigDict(extra="forbid")
