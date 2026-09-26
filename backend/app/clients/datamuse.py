from typing import Any

import httpx

from app.config import DICTIONARY_API


class DatamuseClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    async def fetch_definitions(self, word: str) -> list[dict[str, Any]]:
        response = await self.http_client.get(
            f"{DICTIONARY_API}/words",
            params={
                "sp": word,
                "md": "d",
                "max": 10,
            },
        )
        response.raise_for_status()

        data: list[dict[str, Any]] = response.json()

        definitions: list[dict[str, Any]] = []

        for item in data:
            for definition in item.get("defs", []):
                if "\t" in definition:
                    _, text = definition.split("\t", 1)

                    definitions.append(
                        {
                            "word": item.get("word", word),
                            "definition": text.strip(),
                        }
                    )

        return definitions

    async def fetch_synonyms(self, word: str) -> list[str]:
        response = await self.http_client.get(
            f"{DICTIONARY_API}/words",
            params={
                "rel_syn": word,
                "max": 20,
            },
        )
        response.raise_for_status()

        data: list[dict[str, Any]] = response.json()

        return [
            item["word"]
            for item in data
            if item.get("word")
        ]