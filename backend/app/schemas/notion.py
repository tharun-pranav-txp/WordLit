from pydantic import BaseModel, Field


class ConnectNotionRequest(BaseModel):
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    notion_token: str = Field(
        min_length=1,
        max_length=500,
    )

    parent_page_id: str = Field(
        min_length=1,
        max_length=100,
    )


class ConnectNotionResponse(BaseModel):
    connected: bool


class NotionStatusResponse(BaseModel):
    connected: bool
    data: dict | None = None
    message: str | None = None


class SaveToNotionRequest(BaseModel):
    user_id: str = Field(
        min_length=1,
        max_length=100,
    )

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    content: str = Field(
        min_length=1,
        max_length=20000,
    )


class SaveToNotionResponse(BaseModel):
    id: str
    url: str | None = None