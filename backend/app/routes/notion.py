from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.clients.notion import (
    NotionClient,
    exchange_oauth_code,
)
from app.config import (
    NOTION_OAUTH_CLIENT_ID,
    NOTION_OAUTH_REDIRECT_URI,
)
from app.dependencies import (
    notion_connection_service,
    notion_service,
)
from app.schemas.notion import (
    ConnectNotionRequest,
    ConnectNotionResponse,
    NotionStatusResponse,
    SaveToNotionRequest,
    SaveToNotionResponse,
)


router = APIRouter()


@router.get("/notion/oauth/authorize")
async def notion_oauth_authorize(user_id: str):
    existing_connection = (
        notion_connection_service.get(user_id)
    )

    if existing_connection:
        token = existing_connection.get(
            "notion_token"
        )
        wordlit_page_id = existing_connection.get(
            "wordlit_page_id"
        )

        if token and wordlit_page_id:
            try:
                notion_client = NotionClient(token)

                await notion_client.test_connection()
                await notion_client.get_page(
                    wordlit_page_id
                )

                existing_connection[
                    "auth_type"
                ] = "oauth"

                notion_connection_service.save_oauth_connection(
                    user_id=user_id,
                    access_token=token,
                    workspace_id=existing_connection.get(
                        "workspace_id"
                    ),
                    workspace_name=existing_connection.get(
                        "workspace_name"
                    ),
                    bot_id=existing_connection.get(
                        "bot_id"
                    ),
                    parent_page_id=wordlit_page_id,
                )

                return {
                    "connected": True,
                    "reused": True,
                }

            except Exception:
                pass

    authorization_url = (
        "https://api.notion.com/v1/oauth/authorize"
        f"?client_id={NOTION_OAUTH_CLIENT_ID}"
        "&response_type=code"
        "&owner=user"
        f"&redirect_uri={NOTION_OAUTH_REDIRECT_URI}"
        f"&state={user_id}"
    )

    return RedirectResponse(
        url=authorization_url
    )


@router.get(
    "/notion/oauth/callback"
)
async def notion_oauth_callback(
    code: str,
    state: str,
):
    user_id = state

    try:
        oauth_data = (
            await exchange_oauth_code(
                code
            )
        )

        access_token = oauth_data.get(
            "access_token"
        )

        if not access_token:
            raise ValueError(
                "Notion OAuth returned no access token"
            )

        duplicated_template_id = (
            oauth_data.get(
                "duplicated_template_id"
            )
        )

        notion_connection_service.save_oauth_connection(
            user_id=user_id,
            access_token=access_token,
            workspace_id=oauth_data.get(
                "workspace_id"
            ),
            workspace_name=oauth_data.get(
                "workspace_name"
            ),
            bot_id=oauth_data.get(
                "bot_id"
            ),
            parent_page_id=duplicated_template_id,
        )

        return {
            "connected": True,
        }

    except Exception as exc:
        existing_connection = (
            notion_connection_service.get(
                user_id
            )
        )

        if existing_connection:
            return {
                "connected": True,
            }

        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=502,
            detail=(
                "Notion OAuth failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


@router.get("/notion/oauth/success")
async def notion_oauth_success():
    return {
        "connected": True,
        "message": "Notion connected successfully. You can close this tab.",
    }


@router.post(
    "/notion/connect",
    response_model=ConnectNotionResponse,
)
async def connect_notion(
    request: ConnectNotionRequest,
):
    try:
        # Verify the credentials before storing them.
        client_data = await _test_credentials(
            request.notion_token
        )

        notion_connection_service.save(
            user_id=request.user_id,
            notion_token=request.notion_token,
            parent_page_id=request.parent_page_id,
        )

        return {
            "connected": True,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Notion connection failed: {exc}",
        )


async def _test_credentials(
    token: str,
) -> dict:
    from app.clients.notion import NotionClient

    client = NotionClient(token)

    return await client.test_connection()


@router.get(
    "/notion/status",
    response_model=NotionStatusResponse,
)
async def notion_status(
    user_id: str,
):
    try:
        data = await notion_service.test_connection(
            user_id=user_id,
        )

        return {
            "connected": True,
            "data": data,
        }

    except ValueError as exc:
        return {
            "connected": False,
            "message": str(exc),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Notion connection failed: {exc}",
        )


@router.get("/notion/pages")
async def search_notion_pages(
    user_id: str,
    query: str = "",
):
    try:
        pages = await notion_service.search_pages(
            user_id=user_id,
            query=query,
        )

        return {
            "pages": [
                {
                    "id": page["id"],
                    "url": page.get("url"),
                }
                for page in pages
            ]
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Notion page search failed: {exc}",
        )


@router.post(
    "/notion/save",
    response_model=SaveToNotionResponse,
)
async def save_to_notion(
    request: SaveToNotionRequest,
):
    try:
        return await notion_service.create_page(
            user_id=request.user_id,
            title=request.title,
            content=request.content,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to save to Notion: {exc}",
        )


@router.delete("/notion/disconnect")
async def disconnect_notion(
    user_id: str,
):
    notion_connection_service.delete(
        user_id=user_id,
    )

    return {
        "connected": False,
    }