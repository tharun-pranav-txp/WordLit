from fastapi import APIRouter

from app.dependencies import word_service
from app.schemas.word import WordLookupResponse


router = APIRouter()


@router.get(
    "/lookup",
    response_model=WordLookupResponse,
)
async def lookup(
    word: str,
):
    return await word_service.lookup(word)