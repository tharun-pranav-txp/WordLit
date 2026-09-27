import json

from app.clients.groq import GroqClient


class SummaryService:
    def __init__(
        self,
        groq_client: GroqClient,
    ):
        self.groq_client = groq_client

    async def summarize(
        self,
        text: str,
        max_words: int = 80,
    ) -> dict:
        text = text.strip()

        if not text:
            raise ValueError(
                "Text is required"
            )

        system_prompt = f"""
You are a concise text summarization assistant.

Create a short descriptive title and summarize the user's text.

Rules:
- Preserve the important information.
- Do not invent facts.
- Do not add information that is not present.
- The title should describe the main topic.
- Keep the title concise, preferably 3 to 10 words.
- Do not include dates or times in the title.
- Use simple, natural language.
- The summary must be no more than {max_words} words.
- Return ONLY valid JSON.
- Do not use markdown.
- Do not add any text before or after the JSON.

Return exactly:

{{
    "title": "short descriptive title",
    "summary": "concise summary"
}}
""".strip()

        user_prompt = f"""
Create a suitable title and summarize the following text
in no more than {max_words} words:

{text}
""".strip()

        content = await self.groq_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        content = content.strip()

        if not content:
            raise ValueError(
                "Model returned an empty summary"
            )

        result = self._extract_json_object(
            content
        )

        title = result.get("title")
        summary = result.get("summary")

        if not isinstance(title, str):
            raise ValueError(
                "Model returned no title"
            )

        if not isinstance(summary, str):
            raise ValueError(
                "Model returned no summary"
            )

        title = title.strip()
        summary = summary.strip()

        if not title:
            raise ValueError(
                "Model returned an empty title"
            )

        if not summary:
            raise ValueError(
                "Model returned an empty summary"
            )

        return {
            "title": title,
            "summary": summary,
        }

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
    ) -> dict:
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
                            "Model response is not a JSON object"
                        )

                    return result

        raise ValueError(
            "Incomplete JSON object returned by model"
        )