
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import http_client
from app.routes.health import router as health_router
from app.routes.summary import router as summary_router
from app.routes.word import router as word_router
from app.routes.notion import router as notion_router


# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger("wordlit")


# ------------------------------------------------------------------
# FastAPI application
# ------------------------------------------------------------------

app = FastAPI(
    title="WordLit API",
    version="1.0.0",
)


# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

app.include_router(
    word_router,
)

app.include_router(
    summary_router,
)

app.include_router(
    notion_router,
)

app.include_router(
    health_router,
)


# ------------------------------------------------------------------
# Shutdown
# ------------------------------------------------------------------

@app.on_event("shutdown")
async def shutdown() -> None:
    await http_client.aclose()