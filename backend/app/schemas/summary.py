from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=20000,
    )

    max_words: int = Field(
        default=80,
        ge=20,
        le=300,
    )


class SummarizeResponse(BaseModel):
    title: str
    summary: str