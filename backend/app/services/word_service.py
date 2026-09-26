import asyncio
import json
import logging
from typing import Any

from fastapi import HTTPException
from groq import APIStatusError, RateLimitError

from app.cache.memory import MemoryCache
from app.clients.datamuse import DatamuseClient
from app.clients.groq import GroqClient


logger = logging.getLogger("wordlit")


class WordService:
    def __init__(
        self,
        datamuse_client: DatamuseClient,
        groq_client: GroqClient,
        dictionary_cache: MemoryCache,
        result_cache: MemoryCache,
    ):
        self.datamuse_client = datamuse_client
        self.groq_client = groq_client
        self.dictionary_cache = dictionary_cache
        self.result_cache = result_cache

    async def lookup(
        self,
        word: str,
    ) -> dict:
        word = word.strip().lower()

        if not word:
            raise HTTPException(
                status_code=400,
                detail="word is required",
            )

        if not self._is_valid_lookup_word(word):
            logger.warning(
                "Rejected invalid lookup word: %r",
                word,
            )

            raise HTTPException(
                status_code=400,
                detail="Invalid word",
            )

        cached_result = self.result_cache.get(word)

        if cached_result is not None:
            logger.info(
                "Returning final cache for: %s",
                word,
            )

            return cached_result

        raw = await self._fetch_raw_entry(word)

        if not raw["definitions"]:
            raise HTTPException(
                status_code=404,
                detail=f"No definition found for '{word}'",
            )

        return await self._synthesize(
            word=word,
            raw=raw,
        )

    async def _fetch_raw_entry(
        self,
        word: str,
    ) -> dict:
        cached_entry = self.dictionary_cache.get(word)

        if cached_entry is not None:
            logger.info(
                "Dictionary cache hit: %s",
                word,
            )

            return cached_entry

        definitions, synonyms = await asyncio.gather(
            self.datamuse_client.fetch_definitions(word),
            self.datamuse_client.fetch_synonyms(word),
        )

        result = {
            "definitions": definitions,
            "synonyms": synonyms,
        }

        self.dictionary_cache.set(
            word,
            result,
        )

        logger.info(
            "Datamuse result for %s: %s",
            word,
            result,
        )

        return result

    async def _call_groq(
        self,
        word: str,
        definitions: list[dict],
        synonyms: list[str],
    ) -> dict:
        definitions_json = json.dumps(
            definitions,
            ensure_ascii=False,
        )

        synonyms_json = json.dumps(
            synonyms,
            ensure_ascii=False,
        )

        prompt = f"""
You are a concise dictionary assistant.

Your task is to simplify a dictionary entry.

WORD:

{word}

DICTIONARY DEFINITIONS:

{definitions_json}

SUPPLIED SYNONYMS:

{synonyms_json}

Instructions:

Choose the single most common/general meaning from the
supplied dictionary definitions.

Rewrite that meaning as ONE short, natural sentence that
is easy for an ordinary person to understand.

For synonyms, choose up to 3 words ONLY from the supplied
synonym list.

Never invent synonyms.

If there are no suitable synonyms, use an empty array.

Return ONLY valid JSON.

Do not use markdown.

Do not add any text before or after the JSON.

Return exactly this structure:

{{
    "meaning": "one short clear sentence",
    "synonyms": ["synonym1", "synonym2"]
}}
""".strip()

        logger.info(
            "Sending word=%s to Groq model=%s",
            word,
            self.groq_client.model,
        )

        content = await self.groq_client.generate(
            system_prompt=(
                "Return only valid JSON. "
                "Do not use markdown. "
                "Do not add explanations."
            ),
            user_prompt=prompt,
        )

        logger.info(
            "Groq response for %s: %r",
            word,
            content,
        )

        if not content:
            raise ValueError(
                "Model returned an empty response"
            )

        parsed = self._extract_json_object(
            content
        )

        return self._validate_model_result(
            word=word,
            result=parsed,
            allowed_synonyms=synonyms,
        )

    async def _synthesize(
        self,
        word: str,
        raw: dict,
    ) -> dict:
        cached_result = self.result_cache.get(word)

        if cached_result is not None:
            logger.info(
                "Result cache hit: %s",
                word,
            )

            return cached_result

        definitions = raw["definitions"][:8]
        synonyms = raw["synonyms"][:6]

        if not definitions:
            raise HTTPException(
                status_code=404,
                detail=f"No definition found for '{word}'",
            )

        max_attempts = 3

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            try:
                result = await self._call_groq(
                    word=word,
                    definitions=definitions,
                    synonyms=synonyms,
                )

                self.result_cache.set(
                    word,
                    result,
                )

                logger.info(
                    "Final LLM result for %s: %s",
                    word,
                    result,
                )

                return result

            except RateLimitError as exc:
                logger.warning(
                    "Groq rate limit for word=%s "
                    "attempt=%s/%s: %s",
                    word,
                    attempt,
                    max_attempts,
                    exc,
                )

                if attempt < max_attempts:
                    await asyncio.sleep(
                        2 ** attempt
                    )

            except APIStatusError as exc:
                status_code = getattr(
                    exc,
                    "status_code",
                    None,
                )

                logger.error(
                    "Groq API error for word=%s "
                    "status=%s attempt=%s/%s error=%s",
                    word,
                    status_code,
                    attempt,
                    max_attempts,
                    exc,
                )

                if (
                    status_code in {
                        408,
                        429,
                        500,
                        502,
                        503,
                        504,
                    }
                    and attempt < max_attempts
                ):
                    await asyncio.sleep(
                        2 ** attempt
                    )
                else:
                    break

            except (
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                logger.warning(
                    "Invalid Groq output for word=%s "
                    "attempt=%s/%s: %s",
                    word,
                    attempt,
                    max_attempts,
                    exc,
                )

                if attempt < max_attempts:
                    await asyncio.sleep(
                        0.5 * attempt
                    )

            except Exception:
                logger.exception(
                    "Unexpected Groq error for word=%s "
                    "attempt=%s/%s",
                    word,
                    attempt,
                    max_attempts,
                )

                if attempt < max_attempts:
                    await asyncio.sleep(
                        1 * attempt
                    )

        fallback_definition = definitions[0][
            "definition"
        ].strip()

        fallback_synonyms: list[str] = []

        for synonym in synonyms:
            if synonym.lower() == word.lower():
                continue

            if any(
                existing.lower() == synonym.lower()
                for existing in fallback_synonyms
            ):
                continue

            fallback_synonyms.append(
                synonym
            )

            if len(fallback_synonyms) >= 3:
                break

        fallback_result = {
            "word": word,
            "meaning": fallback_definition,
            "synonyms": fallback_synonyms,
        }

        logger.warning(
            "Using Datamuse fallback for word=%s: %s",
            word,
            fallback_result,
        )

        self.result_cache.set(
            word,
            fallback_result,
        )

        return fallback_result

    @staticmethod
    def _is_valid_lookup_word(
        word: str,
    ) -> bool:
        if not word:
            return False

        if len(word) > 100:
            return False

        allowed = set(
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789"
            "'- "
        )

        return all(
            character in allowed
            for character in word
        )

    @staticmethod
    def _clean_json_content(
        content: str,
    ) -> str:
        content = content.strip()

        if content.startswith("```json"):
            content = content[len("```json"):].strip()

        elif content.startswith("```"):
            content = content[len("```"):].strip()

        if content.endswith("```"):
            content = content[:-3].strip()

        return content

    @classmethod
    def _extract_json_object(
        cls,
        content: str,
    ) -> dict[str, Any]:
        content = cls._clean_json_content(
            content
        )

        try:
            result = json.loads(content)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

        start = content.find("{")

        if start == -1:
            raise ValueError(
                "No JSON object found in model response"
            )

        depth = 0
        in_string = False
        escaped = False

        for index in range(
            start,
            len(content),
        ):
            character = content[index]

            if escaped:
                escaped = False
                continue

            if character == "\\" and in_string:
                escaped = True
                continue

            if character == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if character == "{":
                depth += 1

            elif character == "}":
                depth -= 1

                if depth == 0:
                    candidate = content[
                        start:index + 1
                    ]

                    result = json.loads(
                        candidate
                    )

                    if not isinstance(
                        result,
                        dict,
                    ):
                        raise ValueError(
                            "Model JSON response is not an object"
                        )

                    return result

        raise ValueError(
            "Incomplete JSON object returned by model"
        )

    @staticmethod
    def _validate_model_result(
        word: str,
        result: dict,
        allowed_synonyms: list[str],
    ) -> dict:
        meaning = result.get(
            "meaning",
            "",
        )

        if not isinstance(
            meaning,
            str,
        ):
            meaning = str(meaning)

        meaning = meaning.strip()

        if not meaning:
            raise ValueError(
                "Model returned no meaning"
            )

        model_synonyms = result.get(
            "synonyms",
            [],
        )

        if not isinstance(
            model_synonyms,
            list,
        ):
            model_synonyms = []

        allowed = {
            synonym.lower(): synonym
            for synonym in allowed_synonyms
            if isinstance(
                synonym,
                str,
            )
        }

        final_synonyms: list[str] = []

        for synonym in model_synonyms:
            if not isinstance(
                synonym,
                str,
            ):
                continue

            synonym = synonym.strip()

            if not synonym:
                continue

            original = allowed.get(
                synonym.lower()
            )

            if not original:
                continue

            if original.lower() == word.lower():
                continue

            if any(
                existing.lower() == original.lower()
                for existing in final_synonyms
            ):
                continue

            final_synonyms.append(
                original
            )

            if len(final_synonyms) >= 3:
                break

        return {
            "word": word,
            "meaning": meaning,
            "synonyms": final_synonyms,
        }