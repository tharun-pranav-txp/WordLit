import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import AsyncGroq
import httpx

load_dotenv()

app = FastAPI(title="Word Lookup API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en"
GROQ_MODEL = "openai/gpt-oss-20b"

groq_client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])


async def fetch_raw_entry(word: str) -> dict:
    """Retrieval step: pull real dictionary data to ground the LLM."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{DICTIONARY_API}/{word}")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"No definition found for '{word}'")
    resp.raise_for_status()

    entry = resp.json()[0]

    raw_definitions = []

    for meaning in entry.get("meanings", []):
        part_of_speech = meaning.get("partOfSpeech")
        meaning_synonyms = meaning.get("synonyms", [])
        for d in meaning.get("definitions", []):
            # Keep synonyms scoped to the sense they belong to, so the model
            # can't borrow synonyms from an unrelated meaning of the word.
            sense_synonyms = d.get("synonyms") or meaning_synonyms
            raw_definitions.append({
                "partOfSpeech": part_of_speech,
                "definition": d.get("definition"),
                "synonyms": sense_synonyms[:6],
            })

    return {"definitions": raw_definitions[:5]}


async def synthesize(word: str, raw: dict) -> dict:
    """Generation step: have Groq condense the retrieved data into one meaning + 2-3 synonyms."""
    prompt = (
        f'Word: "{word}"\n\n'
        "Raw dictionary senses (each with its own definition and the synonyms that "
        f"specifically apply to that sense):\n{json.dumps(raw['definitions'], indent=2)}\n\n"
        "Using ONLY the information above, respond with a JSON object with exactly these keys:\n"
        '- "meaning": one clear, concise sentence giving the single most common sense of the word\n'
        '- "synonyms": up to 3 synonyms, taken ONLY from the "synonyms" list of the sense you '
        "chose for \"meaning\" — never from a different sense. If that sense has no synonyms "
        "listed (common for prepositions, conjunctions, and other function words), return an "
        "empty array instead of substituting one\n"
        "Respond with JSON only."
    )

    completion = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=600,
    )

    result = json.loads(completion.choices[0].message.content)

    meaning = str(result.get("meaning", "")).strip()
    synonyms = [str(s).strip() for s in result.get("synonyms", []) if str(s).strip()][:3]

    if not meaning:
        raise HTTPException(status_code=502, detail="Model returned no meaning")

    return {"word": word, "meaning": meaning, "synonyms": synonyms}


@app.get("/lookup")
async def lookup(word: str):
    word = word.strip().lower()
    if not word:
        raise HTTPException(status_code=400, detail="word is required")

    raw = await fetch_raw_entry(word)

    if not raw["definitions"]:
        raise HTTPException(status_code=404, detail=f"No definition found for '{word}'")

    return await synthesize(word, raw)
