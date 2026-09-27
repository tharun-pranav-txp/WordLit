from groq import AsyncGroq

from app.config import GROQ_API_KEY, GROQ_MODEL


class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(
            api_key=GROQ_API_KEY,
        )

        self.model = GROQ_MODEL

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_completion_tokens=2000,
            reasoning_effort="low",
            include_reasoning=False,
        )

        if not completion.choices:
            raise ValueError(
                "Model returned no choices"
            )

        message = completion.choices[0].message

        content = message.content or ""

        if not content.strip():
            raise ValueError(
                "Model returned empty content"
            )

        return content