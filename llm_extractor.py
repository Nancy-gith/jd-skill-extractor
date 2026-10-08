"""
llm_extractor.py
----------------
Extracts skills from a job description using an LLM through the Groq API.

How it works, in short:
1. Read the API key from the .env file (never hardcoded in the code).
2. Send the job description to the model with clear instructions.
3. Ask for JSON output (JSON mode), then parse it safely.
"""

import json
import os

from dotenv import load_dotenv
from groq import BadRequestError, Groq

# Read variables from the .env file into the environment (os.environ).
# This runs once, when the file is imported, so it happens before
# extract_skills_llm() reads GROQ_API_KEY or GROQ_MODEL.
load_dotenv()

# Used when GROQ_MODEL is not set in .env. Change the model in .env
# without touching the code.
DEFAULT_MODEL = "openai/gpt-oss-20b"

# The keys we expect the model to return.
EXPECTED_KEYS = ["technical_skills", "soft_skills", "tools", "experience_requirements"]

# gpt-oss-20b is a reasoning model: it "thinks" (writes hidden reasoning
# tokens) before writing the answer, and both count toward this limit.
# 4000 leaves plenty of room for a long JD's reasoning plus the JSON.
MAX_COMPLETION_TOKENS = 4000

# "low" tells the model to think briefly. Extracting listed skills is an
# easy task, so long reasoning only wastes tokens and time.
REASONING_EFFORT = "low"

# Total tries per request: 1 normal try + 1 automatic retry.
MAX_ATTEMPTS = 2

# Structured outputs: a JSON Schema describing exactly the shape we want.
# With "strict": True, Groq forces the reply to match this schema
# (all 4 keys present, each a list of strings, no extra keys).
SKILLS_SCHEMA = {
    "type": "object",
    "properties": {key: {"type": "array", "items": {"type": "string"}} for key in EXPECTED_KEYS},
    "required": EXPECTED_KEYS,
    "additionalProperties": False,
}

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "jd_skills", "strict": True, "schema": SKILLS_SCHEMA},
}

# The "system" message sets the rules for the model.
# It has 3 parts: the task, the formatting rules, and one worked example
# (a "few-shot" example) that shows the model exactly what we want.
SYSTEM_PROMPT = """You are a precise information extraction assistant.
Read the job description and extract ONLY skills that are explicitly mentioned in it.
Never invent, guess, or add skills that are not written in the text.

Return a JSON object with exactly these keys:
- "technical_skills": techniques, concepts and methods (e.g. python, sql, joins, window functions,
  query optimization, data pipelines, dashboards, a/b testing, machine learning, statistics)
- "soft_skills": interpersonal abilities (e.g. communication, teamwork, stakeholder management)
- "tools": named software, platforms, libraries or cloud services (e.g. excel, power bi, pandas, aws)
- "experience_requirements": years of experience, degrees or certifications, as short phrases
  (e.g. "4+ years in data analysis", "bachelor's degree in statistics")

Rules for technical_skills, soft_skills and tools:
1. Atomic skills: each item is ONE skill of 1-3 words. Split combined phrases into separate items.
2. Include techniques and concepts, not just tool names. If the JD says "write SQL with joins and
   window functions", extract "sql", "joins" and "window functions".
3. Standard names: use the common, plain name in lowercase. Drop filler words such as "strong",
   "excellent", "expert-level", "skills", "experience with". Write "machine learning", not
   "ML-based modelling skills".
4. Put each item in exactly ONE category, and list each item only once. Anything with a product,
   library or brand name (pandas, docker, aws, airflow) goes ONLY in "tools". "technical_skills" is
   only for general techniques and concepts. Exception: programming and query languages (python,
   sql, r) go in "technical_skills".
5. Read the WHOLE text, including "nice to have" sections and lists inside parentheses or joined
   by "or" (e.g. "aws, azure or gcp" gives "aws", "azure", "gcp").
6. If nothing fits a key, return an empty list for it.

Example (only to show the format; never copy these skills unless they appear in the JD):
JD text: "Strong stakeholder management and communication skills. Expert in SQL (joins, CTEs)
and building Tableau dashboards. 3+ years of experience."
Output:
{"technical_skills": ["sql", "joins", "ctes", "dashboards"],
 "soft_skills": ["stakeholder management", "communication"],
 "tools": ["tableau"],
 "experience_requirements": ["3+ years of experience"]}"""


class LLMExtractionError(Exception):
    """Raised when the LLM step fails, with a message that is safe to show the user."""


def get_client() -> Groq:
    """Create a Groq client using the API key from the environment."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMExtractionError(
            "GROQ_API_KEY is missing. Running locally: copy .env.example to .env "
            "and add your key. On Streamlit Community Cloud: add "
            'GROQ_API_KEY = "your-key" under the app\'s Settings → Secrets.'
        )
    return Groq(api_key=api_key)


def parse_llm_json(raw_text: str) -> dict[str, list[str]]:
    """Safely turn the model's text reply into a clean dictionary.

    Input:  the raw string the model returned.
    Output: a dict with all EXPECTED_KEYS, each mapped to a list of strings.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise LLMExtractionError(f"The model did not return valid JSON: {error}") from error

    if not isinstance(data, dict):
        raise LLMExtractionError("The model returned JSON, but not a JSON object.")

    # Make sure every expected key exists and holds a list of strings,
    # even if the model forgot a key or used the wrong type.
    cleaned: dict[str, list[str]] = {}
    for key in EXPECTED_KEYS:
        value = data.get(key, [])
        if not isinstance(value, list):
            value = [value] if value else []
        cleaned[key] = [str(item).strip() for item in value if str(item).strip()]

    return cleaned


def extract_skills_llm(text: str) -> dict[str, list[str]]:
    """Send the job description to Groq and return the extracted skills.

    Input:  the job description as a string.
    Output: {"technical_skills": [...], "soft_skills": [...],
             "tools": [...], "experience_requirements": [...]}
    Raises LLMExtractionError with a friendly message if anything goes wrong.
    """
    client = get_client()
    # "or" also falls back when the line exists but is empty (GROQ_MODEL=).
    model = os.getenv("GROQ_MODEL") or DEFAULT_MODEL

    for attempt in range(1, MAX_ATTEMPTS + 1):
        is_last_attempt = attempt == MAX_ATTEMPTS

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Job description:\n\n{text}"},
                ],
                # Structured outputs: the reply must match SKILLS_SCHEMA.
                response_format=RESPONSE_FORMAT,
                # Room for hidden reasoning tokens + the JSON answer.
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                # Think briefly. Only reasoning models (like gpt-oss) accept this.
                reasoning_effort=REASONING_EFFORT,
                # temperature=0 makes answers as consistent as possible.
                temperature=0,
            )
        except BadRequestError as error:
            # Groq returns 400 "json_validate_failed" when the model's output
            # did not match the schema. That can be a one-off, so try again.
            if "json_validate_failed" in str(error) and not is_last_attempt:
                continue
            raise LLMExtractionError(f"Groq API call failed: {error}") from error
        except Exception as error:  # network problems, bad key, rate limits, etc.
            # Retrying won't fix these, so fail straight away.
            raise LLMExtractionError(f"Groq API call failed: {error}") from error

        raw_text = response.choices[0].message.content or ""
        try:
            return parse_llm_json(raw_text)
        except LLMExtractionError:
            # The reply arrived but was not usable JSON: retry once.
            if not is_last_attempt:
                continue
            raise

    # Not reachable: every path in the loop either returns, continues, or raises.
    raise LLMExtractionError("LLM extraction failed after retrying.")
