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
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
            max_tokens=500,
        )

        if not completion.choices:
            raise ValueError(
                "Model returned no choices"
            )

        message = completion.choices[0].message

        return message.content or ""