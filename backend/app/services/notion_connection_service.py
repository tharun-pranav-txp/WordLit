import json
from pathlib import Path


class NotionConnectionService:
    def __init__(self):
        self.file_path = Path(
            "/app/app/data/notion_connections.json"
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file_path.exists():
            self._write({})

    def _read(self) -> dict:
        with self.file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _write(
        self,
        data: dict,
    ) -> None:
        with self.file_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
            )

    def get(
        self,
        user_id: str,
    ) -> dict | None:
        data = self._read()

        return data.get(user_id)

    def save(
        self,
        user_id: str,
        notion_token: str,
        parent_page_id: str,
    ) -> None:
        data = self._read()

        data[user_id] = {
            "notion_token": notion_token,
            "parent_page_id": parent_page_id,
        }

        self._write(data)

    def save_oauth_connection(
        self,
        user_id: str,
        access_token: str,
        workspace_id: str | None,
        workspace_name: str | None,
        bot_id: str | None,
        parent_page_id: str | None,
    ) -> str | None:
        data = self._read()

        data[user_id] = {
            "notion_token": access_token,
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "bot_id": bot_id,
            "parent_page_id": parent_page_id,
            "auth_type": "oauth",
            "wordlit_page_id": parent_page_id,
        }

        self._write(data)

        if (
            existing_wordlit_page_id
            and parent_page_id
            and existing_wordlit_page_id
            != parent_page_id
        ):
            return parent_page_id

        return None

    def delete(
        self,
        user_id: str,
    ) -> None:
        data = self._read()

        existing = data.get(user_id)

        if not existing:
            return

        existing["auth_type"] = "disconnected"

        data[user_id] = existing

        self._write(data)


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

        data[user_id]["wordlit_page_id"] = page_id

        self._write(data)