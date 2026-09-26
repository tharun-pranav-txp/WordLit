import os

from dotenv import load_dotenv


load_dotenv()


DICTIONARY_API = os.environ["DICTIONARY_API"].rstrip("/")

GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)