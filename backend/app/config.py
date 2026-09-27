import os

from dotenv import load_dotenv


load_dotenv()


DATAMUSE_API = os.environ["DATAMUSE_API"].rstrip("/")

GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

NOTION_PARENT_PAGE_ID = os.getenv(
    "NOTION_PARENT_PAGE_ID"
)

NOTION_OAUTH_CLIENT_ID = os.environ[
    "NOTION_OAUTH_CLIENT_ID"
]

NOTION_OAUTH_CLIENT_SECRET = os.environ[
    "NOTION_OAUTH_CLIENT_SECRET"
]

NOTION_OAUTH_REDIRECT_URI = os.environ[
    "NOTION_OAUTH_REDIRECT_URI"
]
