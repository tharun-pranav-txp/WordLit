import asyncio
import json
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import APIStatusError, AsyncGroq, RateLimitError


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("wordlit")

app = FastAPI(
    title="Word Lookup API",
)


# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------

DICTIONARY_API = os.environ["DICTIONARY_API"].rstrip("/")

GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)


# ------------------------------------------------------------------
# Groq client
# ------------------------------------------------------------------

groq_client = AsyncGroq(
    api_key=GROQ_API_KEY,
)


# ------------------------------------------------------------------
# Shared HTTP client
# ------------------------------------------------------------------

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=2.0,
        read=4.0,
        write=2.0,
        pool=2.0,
    ),
    limits=httpx.Limits(
        max_connections=50,
        max_keepalive_connections=20,
    ),
)


# ------------------------------------------------------------------
# Caches
# ------------------------------------------------------------------

# Raw Datamuse results.
dictionary_cache: dict[str, dict] = {}

# Successful/fallback final results.
result_cache: dict[str, dict] = {}


# ------------------------------------------------------------------
# Shutdown
# ------------------------------------------------------------------

@app.on_event("shutdown")
async def shutdown() -> None:
    await http_client.aclose()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def is_valid_lookup_word(word: str) -> bool:
    """
    Basic validation for lookup input.

    Prevents accidental requests such as:

        GROQ_MODEL=openai/gpt-oss-20b

    from being treated as dictionary words.
    """

    if not word:
        return False

    if len(word) > 100:
        return False

    # Allow letters, numbers, apostrophes, hyphens and spaces.
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


def clean_json_content(content: str) -> str:
    """
    Remove common markdown fences around JSON.
    """

    content = content.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()

    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    return content


def extract_json_object(content: str) -> dict[str, Any]:
    """
    Parse a JSON object from model output.

    Handles cases where a model accidentally puts a small
    amount of text before or after the JSON.
    """

    content = clean_json_content(content)

    # First try the entire response.
    try:
        result = json.loads(content)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # Try to find the first complete JSON object.
    start = content.find("{")

    if start == -1:
        raise ValueError(
            "No JSON object found in model response"
        )

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(content)):
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

                result = json.loads(candidate)

                if not isinstance(result, dict):
                    raise ValueError(
                        "Model JSON response is not an object"
                    )

                return result

    raise ValueError(
        "Incomplete JSON object returned by model"
    )


def validate_model_result(
    word: str,
    result: dict,
    allowed_synonyms: list[str],
) -> dict:
    """
    Validate and normalize the model response.
    """

    meaning = result.get(
        "meaning",
        "",
    )

    if not isinstance(meaning, str):
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

    if not isinstance(model_synonyms, list):
        model_synonyms = []

    # Map lowercase -> original Datamuse spelling.
    allowed = {
        synonym.lower(): synonym
        for synonym in allowed_synonyms
        if isinstance(synonym, str)
    }

    final_synonyms: list[str] = []

    for synonym in model_synonyms:
        if not isinstance(synonym, str):
            continue

        synonym = synonym.strip()

        if not synonym:
            continue

        original = allowed.get(
            synonym.lower()
        )

        if not original:
            continue

        # Never return the lookup word itself.
        if original.lower() == word.lower():
            continue

        # Remove duplicates.
        if any(
            existing.lower() == original.lower()
            for existing in final_synonyms
        ):
            continue

        final_synonyms.append(original)

        if len(final_synonyms) >= 3:
            break

    return {
        "word": word,
        "meaning": meaning,
        "synonyms": final_synonyms,
    }


# ------------------------------------------------------------------
# Datamuse definitions
# ------------------------------------------------------------------

async def fetch_definitions(
    word: str,
) -> list[dict]:
    """
    Fetch definitions from Datamuse.
    """

    try:
        response = await http_client.get(
            f"{DICTIONARY_API}/words",
            params={
                "sp": word,
                "md": "d",
                "max": 1,
            },
        )

        response.raise_for_status()

    except httpx.TimeoutException:
        logger.exception(
            "Datamuse definitions timeout: %s",
            word,
        )

        raise HTTPException(
            status_code=504,
            detail="Dictionary service timed out",
        )

    except httpx.RequestError as exc:
        logger.exception(
            "Datamuse definitions request failed: %s",
            word,
        )

        raise HTTPException(
            status_code=502,
            detail="Dictionary service unavailable",
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.exception(
            "Datamuse definitions HTTP error: %s",
            word,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Dictionary service returned "
                f"HTTP {exc.response.status_code}"
            ),
        ) from exc

    try:
        entries = response.json()

    except ValueError as exc:
        logger.exception(
            "Invalid Datamuse JSON for word=%s",
            word,
        )

        raise HTTPException(
            status_code=502,
            detail="Dictionary service returned invalid data",
        ) from exc

    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"No definition found for '{word}'",
        )

    entry = entries[0]

    definitions: list[dict] = []

    for raw_definition in entry.get(
        "defs",
        [],
    ):
        if "\t" in raw_definition:
            part_of_speech, definition = (
                raw_definition.split(
                    "\t",
                    1,
                )
            )
        else:
            part_of_speech = ""
            definition = raw_definition

        definition = definition.strip()

        if not definition:
            continue

        definitions.append(
            {
                "partOfSpeech": part_of_speech,
                "definition": definition,
            }
        )

    return definitions[:8]


# ------------------------------------------------------------------
# Datamuse synonyms
# ------------------------------------------------------------------

async def fetch_synonyms(
    word: str,
) -> list[str]:
    """
    Fetch synonyms from Datamuse.

    Synonyms are optional.
    """

    try:
        response = await http_client.get(
            f"{DICTIONARY_API}/words",
            params={
                "rel_syn": word,
                "max": 10,
            },
        )

        response.raise_for_status()

        entries = response.json()

        synonyms = [
            item["word"]
            for item in entries
            if item.get("word")
        ]

        return synonyms[:6]

    except Exception:
        logger.warning(
            "Could not retrieve synonyms for word=%s",
            word,
            exc_info=True,
        )

        return []


# ------------------------------------------------------------------
# Datamuse combined retrieval
# ------------------------------------------------------------------

async def fetch_raw_entry(
    word: str,
) -> dict:
    """
    Retrieve definitions and synonyms concurrently.
    """

    if word in dictionary_cache:
        logger.info(
            "Dictionary cache hit: %s",
            word,
        )

        return dictionary_cache[word]

    definitions, synonyms = await asyncio.gather(
        fetch_definitions(word),
        fetch_synonyms(word),
    )

    result = {
        "definitions": definitions,
        "synonyms": synonyms,
    }

    dictionary_cache[word] = result

    logger.info(
        "Datamuse result for %s: %s",
        word,
        result,
    )

    return result


# ------------------------------------------------------------------
# Groq request
# ------------------------------------------------------------------

async def call_groq(
    word: str,
    definitions: list[dict],
    synonyms: list[str],
) -> dict:
    """
    Call Groq and return the parsed/validated result.

    We intentionally do NOT use response_format.

    The application performs JSON validation itself.
    """

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
        GROQ_MODEL,
    )

    completion = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only valid JSON. "
                    "Do not use markdown. "
                    "Do not add explanations."
                ),
            },
            {
                "role": "user",
                "content": prompt,
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

    content = message.content

    logger.info(
        "Groq response for %s: %r",
        word,
        content,
    )

    if not content:
        raise ValueError(
            "Model returned an empty response"
        )

    parsed = extract_json_object(content)

    return validate_model_result(
        word=word,
        result=parsed,
        allowed_synonyms=synonyms,
    )


# ------------------------------------------------------------------
# Groq synthesis with retry
# ------------------------------------------------------------------

async def synthesize(
    word: str,
    raw: dict,
) -> dict:
    """
    Use Groq to simplify the Datamuse result.

    If Groq temporarily fails, retry.

    If all attempts fail, return the original dictionary
    definition rather than returning HTTP 502.
    """

    # --------------------------------------------------------------
    # Cache
    # --------------------------------------------------------------

    if word in result_cache:
        logger.info(
            "Result cache hit: %s",
            word,
        )

        return result_cache[word]

    definitions = raw["definitions"][:8]

    synonyms = raw["synonyms"][:6]

    if not definitions:
        raise HTTPException(
            status_code=404,
            detail=f"No definition found for '{word}'",
        )

    # --------------------------------------------------------------
    # Retry Groq
    # --------------------------------------------------------------

    max_attempts = 3

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            result = await call_groq(
                word=word,
                definitions=definitions,
                synonyms=synonyms,
            )

            result_cache[word] = result

            logger.info(
                "Final LLM result for %s: %s",
                word,
                result,
            )

            return result

        # ----------------------------------------------------------
        # Rate limit
        # ----------------------------------------------------------

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

        # ----------------------------------------------------------
        # Groq HTTP errors
        # ----------------------------------------------------------

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

            # Retry server/rate-limit errors.
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

        # ----------------------------------------------------------
        # JSON/model output errors
        # ----------------------------------------------------------

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

        # ----------------------------------------------------------
        # Unexpected errors
        # ----------------------------------------------------------

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

    # --------------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------------

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

    # Cache fallback too, so repeated requests don't repeatedly
    # hammer Groq for the same word.
    result_cache[word] = fallback_result

    return fallback_result


# ------------------------------------------------------------------
# API
# ------------------------------------------------------------------

@app.get("/lookup")
async def lookup(
    word: str,
):
    """
    Word lookup flow:

        Client
          ↓
        FastAPI
          ↓
        Datamuse
          ↓
        Groq LLM
          ↓
        JSON validation
          ↓
        simplified result

    If Groq fails after retries:

        Datamuse definition
          ↓
        fallback result
    """

    word = word.strip().lower()

    # --------------------------------------------------------------
    # Validate input
    # --------------------------------------------------------------

    if not word:
        raise HTTPException(
            status_code=400,
            detail="word is required",
        )

    if not is_valid_lookup_word(word):
        logger.warning(
            "Rejected invalid lookup word: %r",
            word,
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid word",
        )

    # --------------------------------------------------------------
    # Final cache
    # --------------------------------------------------------------

    if word in result_cache:
        logger.info(
            "Returning final cache for: %s",
            word,
        )

        return result_cache[word]

    # --------------------------------------------------------------
    # Datamuse
    # --------------------------------------------------------------

    raw = await fetch_raw_entry(word)

    if not raw["definitions"]:
        raise HTTPException(
            status_code=404,
            detail=f"No definition found for '{word}'",
        )

    # --------------------------------------------------------------
    # Groq + fallback
    # --------------------------------------------------------------

    return await synthesize(
        word=word,
        raw=raw,
    )
