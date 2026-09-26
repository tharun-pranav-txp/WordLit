from pydantic import BaseModel


class WordLookupResponse(BaseModel):
    word: str
    meaning: str
    synonyms: list[str]