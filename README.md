# JD Skill Extractor

A small Streamlit app that pulls skills out of a job description (JD) in two ways and shows them side by side:

- **Classical NLP (spaCy):** a `PhraseMatcher` searches for skills from a hand-written list.
- **LLM (Groq):** a large language model reads the JD and returns JSON.

A **Comparison** section then shows which skills only one method found.

## Project structure

```
JD Skill Extractor/
├── app.py                  # Streamlit UI
├── classical_extractor.py  # spaCy PhraseMatcher logic
├── llm_extractor.py        # Groq API call + safe JSON parsing
├── skill_cleanup.py        # Cleans LLM output: long phrases, aliases, categories, duplicates
├── skills_list.py          # Hand-written skills + alias map
├── requirements.txt        # Pinned package versions
├── .env.example            # Template for your API key
└── docs/
    ├── HOW_IT_WORKS.md
    ├── KNOWLEDGE_GRAPH.md
    └── INTERVIEW_QA.md
```

## Setup

```bash
# 1. (Optional) create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Groq API key (free at https://console.groq.com/keys)
copy .env.example .env       # Windows  (macOS/Linux: cp .env.example .env)
# then open .env and paste your key

# 4. Run the app
streamlit run app.py
```

**LLM model:** the default is `openai/gpt-oss-20b` on Groq. To use a different model, add a line like `GROQ_MODEL=openai/gpt-oss-120b` to your `.env` (see https://console.groq.com/docs/models).

No spaCy model download is needed. The app uses `spacy.blank("en")`, which only needs the built-in English tokenizer.

## Error handling

| Situation | What the app does |
|---|---|
| Empty text box | Shows a warning and stops |
| `GROQ_API_KEY` missing | spaCy results still show; the LLM column shows how to fix it |
| API failure (network, bad key, rate limit) | Error shown in the LLM column |
| Model returns invalid JSON or fails schema validation | Retried once automatically; if it fails again, shown as an error |
| Model leaves out a key or uses the wrong type | Filled in with an empty list |

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub. `.env` is git-ignored, so your key stays on your computer.
2. At https://share.streamlit.io, click **Create app**, pick this repo, branch `main`, and main file `app.py`.
3. Under **Advanced settings → Secrets**, paste:
   ```toml
   GROQ_API_KEY = "your-groq-key"
   # GROQ_MODEL = "openai/gpt-oss-120b"   # optional
   ```
4. Click **Deploy**.

Top-level secrets are also exposed as environment variables, so the code reads them with `os.getenv` and needs no changes.

## Learn more

Read the files in [docs/](docs/). They explain every part of the project in simple words.
