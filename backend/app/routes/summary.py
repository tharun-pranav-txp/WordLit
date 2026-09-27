import logging

from fastapi import APIRouter, HTTPException

from app.dependencies import summary_service
from app.schemas.summary import (
    SummarizeRequest,
    SummarizeResponse,
)


logger = logging.getLogger("wordlit.summary")

router = APIRouter()


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
)
async def summarize(
    request: SummarizeRequest,
):
    try:
        return await summary_service.summarize(
            text=request.text,
            max_words=request.max_words,
        )

    except ValueError as exc:
        logger.error(
            "Summary validation error: %s",
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "Unexpected summary error"
        )

        raise HTTPException(
            status_code=500,
            detail="Internal summary error",
        )