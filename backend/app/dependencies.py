import httpx

from app.cache.memory import MemoryCache
from app.clients.datamuse import DatamuseClient
from app.clients.groq import GroqClient
from app.services.word_service import WordService


http_client = httpx.AsyncClient()

datamuse_client = DatamuseClient(
    http_client=http_client,
)

groq_client = GroqClient()

dictionary_cache = MemoryCache()
result_cache = MemoryCache()

word_service = WordService(
    datamuse_client=datamuse_client,
    groq_client=groq_client,
    dictionary_cache=dictionary_cache,
    result_cache=result_cache,
)