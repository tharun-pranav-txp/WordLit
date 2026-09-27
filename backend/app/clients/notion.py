import httpx
import base64

from notion_client import AsyncClient

from app.config import (
    NOTION_OAUTH_CLIENT_ID,
    NOTION_OAUTH_CLIENT_SECRET,
    NOTION_OAUTH_REDIRECT_URI,
)


class NotionClient:
    def __init__(
        self,
        token: str,
    ):
        self.client = AsyncClient(
            auth=token,
        )

    async def test_connection(self) -> dict:
        response = await self.client.users.me()

        return {
            "id": response["id"],
            "name": response.get("name"),
            "type": response.get("type"),
        }

    async def get_page(
        self,
        page_id: str,
    ) -> dict:
        response = await self.client.pages.retrieve(
            page_id=page_id
        )

        return response

    async def archive_page(
        self,
        page_id: str,
    ) -> dict:
        return await self.client.pages.update(
            page_id=page_id,
            archived=True,
        )
        
    async def search_pages(
        self,
        query: str,
    ) -> list[dict]:
        response = await self.client.search(
            query=query,
            filter={
                "property": "object",
                "value": "page",
            },
        )

        return response.get(
            "results",
            [],
        )

    async def create_page(
        self,
        parent_page_id: str,
        title: str,
        content: str,
    ) -> dict:
        try:
            response = await self.client.pages.create(
                parent={
                    "page_id": parent_page_id
                },
                properties={
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": content
                                    }
                                }
                            ]
                        }
                    }
                ],
            )

            return {
                "id": response["id"],
                "url": response.get("url"),
            }

        except Exception as exc:
            print(
                "NOTION CREATE PAGE ERROR:",
                type(exc).__name__,
                str(exc),
            )
            raise


async def exchange_oauth_code(
    code: str,
) -> dict:
    credentials = (
        f"{NOTION_OAUTH_CLIENT_ID}:"
        f"{NOTION_OAUTH_CLIENT_SECRET}"
    )

    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.notion.com/v1/oauth/token",
            headers={
                "Authorization":
                    f"Basic {encoded_credentials}",
                "Content-Type":
                    "application/json",
            },
            json={
                "grant_type":
                    "authorization_code",
                "code": code,
                "redirect_uri":
                    NOTION_OAUTH_REDIRECT_URI,
            },
        )

        response.raise_for_status()

        return response.json()