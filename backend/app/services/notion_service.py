from app.clients.notion import NotionClient
from app.services.notion_connection_service import (
    NotionConnectionService,
)


class NotionService:
    def __init__(
        self,
        notion_connection_service: NotionConnectionService,
    ):
        self.notion_connection_service = (
            notion_connection_service
        )

    async def _get_client(
        self,
        user_id: str,
    ) -> tuple[NotionClient, str]:
        connection = (
            self.notion_connection_service.get(
                user_id
            )
        )

        if not connection:
            raise ValueError(
                "Notion is not connected"
            )

        if connection.get("auth_type") == "disconnected":
            raise ValueError(
                "Notion is not connected"
            )

        token = connection.get(
            "notion_token"
        )

        wordlit_page_id = connection.get(
            "wordlit_page_id"
        )

        fallback_page_id = connection.get(
            "parent_page_id"
        )

        if not token:
            raise ValueError(
                "Notion token is not configured"
            )

        if not wordlit_page_id:
            raise ValueError(
                "WordLit Notion page is not configured"
            )

        client = NotionClient(token)

        try:
            page = await client.get_page(
                wordlit_page_id
            )

            if page.get("archived") is True:
                await client.unarchive_page(
                    wordlit_page_id
                )

            return (
                client,
                wordlit_page_id,
            )

        except Exception:
            if (
                not fallback_page_id
                or fallback_page_id
                == wordlit_page_id
            ):
                raise ValueError(
                    "WordLit Notion page is no longer accessible"
                )

            await client.get_page(
                fallback_page_id
            )

            self.notion_connection_service.update_wordlit_page(
                user_id=user_id,
                page_id=fallback_page_id,
            )

            return (
                client,
                fallback_page_id,
            )

    async def test_connection(
        self,
        user_id: str,
    ) -> dict:
        client, _ = await self._get_client(
            user_id
        )

        return await client.test_connection()

    async def search_pages(
        self,
        user_id: str,
        query: str,
    ) -> list[dict]:
        client, _ = await self._get_client(
            user_id
        )

        return await client.search_pages(
            query=query,
        )

    async def create_page(
        self,
        user_id: str,
        title: str,
        content: str,
    ) -> dict:
        client, wordlit_page_id = (
            await self._get_client(user_id)
        )

        return await client.create_page(
            parent_page_id=wordlit_page_id,
            title=title,
            content=content,
        )

    def update_wordlit_page(
        self,
        user_id: str,
        page_id: str,
    ) -> None:
        data = self._read()

        if user_id not in data:
            raise ValueError(
                "Notion connection not found"
            )

        data[user_id][
            "wordlit_page_id"
        ] = page_id

        self._write(data)