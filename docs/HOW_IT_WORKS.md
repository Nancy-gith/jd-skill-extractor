# How JD Skill Extractor Works

A beginner-friendly walkthrough of the whole project.

---

## 1. What the app does (in 3 lines)

1. You paste a job description (JD) into a text box.
2. The app finds the skills in it two ways: a **rule-based** way (spaCy) and an **AI** way (an LLM on Groq).
3. It shows both results side by side and tells you which skills each method found that the other missed.

---

## 2. The journey of a job description, step by step

Imagine you paste this JD:

> "We need a Data Analyst with strong **SQL** and **Python** skills, experience with **Power BI**, and excellent **communication**. 2+ years of experience required."

Here is what happens:

1. **You paste and click.** Streamlit stores your text in the variable `jd_text`. Clicking **Extract Skills** makes `st.button(...)` return `True`.
2. **Empty check.** If the text is empty (or only spaces), the app shows a warning and calls `st.stop()`. Nothing else runs.
3. **Classical path (left column).** `app.py` calls `extract_skills_classical(jd_text)`:
   - If the JD has an **"About the company"** section, it is skipped first (see fix 4 in "Cleaning up after the LLM" in section 5).
   - spaCy splits the text into tokens: `["We", "need", "a", "Data", "Analyst", "with", "strong", "SQL", ...]`.
   - The PhraseMatcher compares those tokens with every skill in `skills_list.py`.
   - Matches are grouped: Technical → `Python, SQL`; Soft → `communication`; Tools → `Power BI`.
4. **LLM path (right column).** `app.py` calls `extract_skills_llm(jd_text)`:
   - The API key is read from `.env`.
   - The JD and instructions are sent to Groq over the internet. The default model is **`openai/gpt-oss-20b`**, an open-weight model from OpenAI that Groq hosts. You can switch models by setting `GROQ_MODEL` in `.env`, with no code change.
   - The request asks for **structured output** (JSON that must match our schema), allows up to **4000 output tokens**, and sets **reasoning effort to "low"**. Section 5 explains all three.
   - If Groq says the JSON failed validation, or the reply can't be parsed, the app **automatically tries once more**.
   - The model replies with JSON text such as `{"technical_skills": ["SQL", "Python"], "tools": ["Power BI"], ...}`.
   - `json.loads` turns the text into a Python dictionary, and missing keys are filled with empty lists.
   - `skill_cleanup.py` fixes the model's common slips with plain Python rules: it drops long phrases, merges name variants, moves tools into the tools list, and removes duplicates.
   - Unlike spaCy, it can also find `experience_requirements: ["2+ years of experience"]`.
5. **Comparison.** Both results are flattened into **sets** of lowercase skill names. Set math finds the differences:
   - `llm_skills - spacy_skills` → found only by the LLM
   - `spacy_skills - llm_skills` → found only by spaCy
   - `spacy_skills & llm_skills` → found by both
6. **Display.** Streamlit draws everything on the page.

If the LLM step fails (no key, no internet, bad JSON), the spaCy column **still works**, and the LLM column shows a clear error.

---

## 3. Each file explained

| File | What it does | Why it exists |
|---|---|---|
| `skills_list.py` | Holds `SKILLS` (~80 skills in 3 categories) and `SKILL_ALIASES` (different spellings of the same skill → one standard name). | Keeps the **data** apart from the **logic**. To add a skill or a spelling, you edit only this file. |
| `classical_extractor.py` | Builds a spaCy PhraseMatcher and finds skills from the list. | The "classical NLP" method: fast, free, offline, predictable. |
| `llm_extractor.py` | Calls the Groq API, asks for JSON, and parses it safely. | The "LLM" method: understands context and finds skills that aren't in any list. |
| `skill_cleanup.py` | Cleans the LLM's lists in 4 steps: long phrases, aliases, misplaced tools, duplicates. | The prompt works *most* of the time. These rules fix the common slips *every* time. Keeping them in their own file keeps `llm_extractor.py` about talking to Groq. |
| `app.py` | The Streamlit web page: text box, button, columns, comparison. | The **UI layer**. It only shows things; the real work happens in the extractor files. |
| `requirements.txt` | Lists the Python packages to install. | So anyone can run `pip install -r requirements.txt` and get the same setup. |
| `.env.example` | A template that shows which secrets are needed. | People copy it to `.env` and add their own key. The real `.env` is never shared. |
| `.gitignore` | Tells Git which files to ignore (including `.env`). | Stops your API key from being uploaded to GitHub by accident. |

---

## 4. Important functions explained

### `build_matcher()` — in `classical_extractor.py`
- **Input:** nothing (it reads `SKILLS` from `skills_list.py`).
- **Output:** a ready-to-use `PhraseMatcher`.
- **Inside:** It creates a matcher with `attr="LOWER"` so case doesn't matter. For each category, it turns every skill string into a spaCy `Doc` (a tokenized version) and adds the list under the category name as a label.

### `normalize(skill)` — in `classical_extractor.py`
- **Input:** a string such as `"Problem-Solving"`.
- **Output:** `"problem solving"` (lowercase, hyphens turned into spaces).
- **Why:** so `"problem-solving"` and `"problem solving"` count as the same skill, and so the comparison doesn't fail just because of different capital letters.

### `extract_skills_classical(text)` — in `classical_extractor.py`
- **Input:** the JD as a string.
- **Output:** `{"Technical Skills": [...], "Soft Skills": [...], "Tools": [...]}`.
- **Inside:**
  1. `doc = nlp(text)` tokenizes the JD.
  2. `matcher(doc)` returns a list of `(match_id, start, end)` tuples.
  3. `match_id` is turned back into the category name. `doc[start:end]` is the matched text.
  4. Each skill is added to a **set**, so a skill mentioned 3 times appears once.
  5. The sets are turned into sorted lists.

### `get_client()` — in `llm_extractor.py`
- **Input:** nothing (it reads `GROQ_API_KEY` from the environment).
- **Output:** a `Groq` client object.
- **Inside:** If the key is missing, it raises `LLMExtractionError` with a helpful message instead of crashing.

### `parse_llm_json(raw_text)` — in `llm_extractor.py`
- **Input:** the raw text the model returned.
- **Output:** a clean dict with all 4 expected keys, each a list of strings.
- **Inside:** `json.loads` sits inside `try/except`. If the JSON is broken, we raise a friendly error. If a key is missing or isn't a list, we fix it.

### `remove_about_section(text)` — in `classical_extractor.py`
- **Input:** the JD as a string.
- **Output:** `(text_to_search, removed_text)`.
- **Inside:** It looks for a company heading ("About Us", "About the company", "About KiteFishAI", "Who we are"). It removes everything from that heading to the next heading. "About the role" and "About you" are **kept**, because they describe the job. `extract_skills_classical` calls it first, and `app.py` calls it to show which section was skipped.

### `clean_llm_skills(result)` — in `skill_cleanup.py`
- **Input:** the parsed LLM result (all 4 keys).
- **Output:** the cleaned result, plus a new key `removed_phrases`.
- **Inside:** It runs 5 small functions, in this order:
  1. `drop_long_phrases`: items over 4 words are removed and kept aside in `removed_phrases`.
  2. `apply_aliases`: every skill is looked up in `SKILL_ALIASES` (`"forecasts"` → `"forecasting"`).
  3. `apply_known_categories`: any skill that is in `skills_list.py` is moved to the category it has there (`python` → technical skills, `tensorflow` → tools), the same category spaCy uses.
  4. `strip_soft_suffixes`: soft skills lose a trailing "skills" (`"presentation skills"` → `"presentation"`).
  5. `deduplicate_skills`: removes items that match after lowercasing, removing "skills", and making the last word singular.

  `experience_requirements` isn't touched. See "Cleaning up after the LLM" in section 5.

### `extract_skills_llm(text)` — in `llm_extractor.py`
- **Input:** the JD as a string.
- **Output:** `{"technical_skills": [...], "soft_skills": [...], "tools": [...], "experience_requirements": [...]}`.
- **Inside:** It gets a client and picks the model with `os.getenv("GROQ_MODEL") or DEFAULT_MODEL` (default `openai/gpt-oss-20b`). It sends a **system message** (the rules) and a **user message** (the JD) with these settings:
  - `response_format=RESPONSE_FORMAT`: structured output, so the reply must match `SKILLS_SCHEMA`.
  - `max_completion_tokens=4000`: enough room for the model's thinking plus the JSON.
  - `reasoning_effort="low"`: think briefly, because this is an easy task.
  - `temperature=0`: as consistent as possible.

  Then it passes the reply to `parse_llm_json`. This all happens inside a loop that runs **at most 2 times** (`MAX_ATTEMPTS = 2`):
  - If Groq returns a `json_validate_failed` error, or `parse_llm_json` fails → try again (only once).
  - If the error is something a retry can't fix (wrong API key, no internet, rate limit) → stop straight away.
  - Any final failure becomes an `LLMExtractionError`, which `app.py` shows in red.

### `show_skill_groups(groups)` and `all_skills_normalized(groups)` — in `app.py`
- `show_skill_groups`: draws each category heading with its skills underneath.
- `all_skills_normalized`: flattens `{"Tools": ["Excel"], "Soft Skills": ["teamwork"]}` into `{"excel", "teamwork"}` so we can compare with set math.

---

## 5. New concepts, explained simply

### Tokenization
Breaking text into small pieces called **tokens** (usually words and punctuation).

```python
nlp = spacy.blank("en")
doc = nlp("I know Power BI, SQL.")
print([t.text for t in doc])
# ['I', 'know', 'Power', 'BI', ',', 'SQL', '.']
```

Computers can't "read" a sentence the way we do. Tokens are the units they work with. The PhraseMatcher compares tokens, not raw characters, so `"SQL,"` still matches `"SQL"` because the comma is its own token.

### PhraseMatcher
A spaCy tool that quickly finds **exact phrases** from a list inside a text, even multi-word phrases like "machine learning".

```python
from spacy.matcher import PhraseMatcher
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")  # ignore case
matcher.add("Tools", [nlp.make_doc("Power BI")])

doc = nlp("Experience with POWER BI is a plus")
for match_id, start, end in matcher(doc):
    print(doc[start:end].text)   # POWER BI
```

- `attr="LOWER"` → compare lowercase versions, so `POWER BI` = `Power BI`.
- It's fast even with thousands of phrases.
- It **cannot** find synonyms or skills that aren't in its list.

### API calls
An **API** (Application Programming Interface) is a way for one program to ask another program for something over the internet.

```python
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "Say hi"}],
)
print(response.choices[0].message.content)   # "Hi!"
```

Our app sends the JD to Groq's servers, a model runs there, and the answer comes back. Calls can fail (no internet, wrong key, too many requests), so we wrap them in `try/except`.

### JSON mode
**JSON** is a text format for structured data: `{"tools": ["Excel", "SQL"]}`.

Normally an LLM can reply with anything, like "Sure! Here are the skills: ...". That is hard for code to read. **JSON mode** (`response_format={"type": "json_object"}`) tells the API to only return valid JSON. We still use `try/except` around `json.loads` in case something unexpected comes back, because good code never fully trusts outside data.

```python
import json
data = json.loads('{"tools": ["Excel"]}')
print(data["tools"])   # ['Excel']
```

### Structured outputs (JSON Schema): what the app uses now
JSON mode only promises *some* valid JSON. The model could still forget a key or return `"tools": "Excel"` (a string instead of a list).

**Structured outputs** go one step further. We give the API a **JSON Schema**, a description of the exact shape we want:

```python
SKILLS_SCHEMA = {
    "type": "object",
    "properties": {
        "technical_skills": {"type": "array", "items": {"type": "string"}},
        # ... same for soft_skills, tools, experience_requirements
    },
    "required": ["technical_skills", "soft_skills", "tools", "experience_requirements"],
    "additionalProperties": False,   # no extra keys allowed
}
response_format = {"type": "json_schema",
                   "json_schema": {"name": "jd_skills", "strict": True, "schema": SKILLS_SCHEMA}}
```

With `"strict": True`, Groq makes the model's output follow this shape: all 4 keys present, each one a list of strings. Think of it like a form with fixed boxes instead of a blank page. `gpt-oss-20b` supports strict mode on Groq. We **still** keep `try/except` and `parse_llm_json` as a safety net.

### Tokens and `max_completion_tokens`
LLMs read and write in **tokens**: small chunks of text, roughly ¾ of a word each. (These are different from spaCy's tokens, which are whole words.) `"Power BI dashboards"` might be 4–5 LLM tokens.

`max_completion_tokens` is the **maximum number of tokens the model may write** in its reply. If it hits that limit, it stops mid-sentence. For JSON, that means a half-written `{"tools": ["Exc` that can't be parsed. We set it to **4000** so a long JD never runs out of room.

### Reasoning tokens and `reasoning_effort`
`gpt-oss-20b` is a **reasoning model**. Before it writes the answer, it first "thinks" in private: it writes notes to itself like *"The JD mentions SQL and Power BI… Power BI is a tool…"*. Those private notes are called **reasoning tokens**.

Two things to know:
1. **You don't see them**, but they still **count toward `max_completion_tokens`**.
2. If the model thinks for too long, it can use up the whole limit **before writing any JSON**. That is exactly what caused the earlier `json_validate_failed` error with an empty `failed_generation` on long JDs: the budget was spent on thinking, and nothing was left for the answer.

```
Token budget: 4000
[ reasoning tokens (hidden) ][ JSON answer (what we get) ][ unused ]
```

`reasoning_effort` tells the model how hard to think: `"low"`, `"medium"`, or `"high"`. Picking skills out of a JD is an easy task, so we use **`"low"`**. That means less thinking, faster replies, and more room for the JSON. In our 597-word test JD, the model used only **4 reasoning tokens** and 381 tokens in total, far below the 4000 limit.

Note: only reasoning models accept `reasoning_effort`. If you set `GROQ_MODEL` to a non-reasoning model, remove that line from `llm_extractor.py`.

### Automatic retry
LLMs are not 100% predictable. A request can fail once and succeed on the next try. So the app uses a small loop:

```python
for attempt in range(1, MAX_ATTEMPTS + 1):   # MAX_ATTEMPTS = 2
    try:
        response = client.chat.completions.create(...)
    except BadRequestError as error:
        if "json_validate_failed" in str(error) and not is_last_attempt:
            continue        # try again
        raise LLMExtractionError(...)
```

- **Retry:** JSON validation failed, or the reply couldn't be parsed. These are often one-off problems.
- **Don't retry:** a wrong API key, no internet, or a rate limit. Trying again immediately won't help, and it wastes time and quota.
- Only **one** retry, so a broken request never loops forever.

### Prompt design: atomic skills and a few-shot example
The **prompt** is the instructions we send to the model (`SYSTEM_PROMPT` in `llm_extractor.py`). The model does what the prompt says, so a vague prompt gives vague results.

**The problem with the first prompt.** It only said "extract skills", so the model returned whole phrases:

```
"strong stakeholder management and communication skills"   ← 1 long item
```

That's hard to compare with spaCy, which finds `stakeholder management` and `communication` as 2 separate items. The model also listed tool names but skipped techniques like *joins* or *window functions*.

**What the new prompt adds:**

| Rule | Why |
|---|---|
| **Atomic skills**: each item is 1–3 words, and combined phrases are split | One skill per item, like spaCy |
| **Include techniques and concepts** (joins, window functions, dashboards, data pipelines, query optimization) | A JD asks for more than tool names |
| **Standard lowercase names**, with filler words dropped ("strong", "expert-level", "skills") | `"Expert-level SQL"` becomes `"sql"`, which matches spaCy's `"SQL"` after `normalize()` |
| **Each item in exactly one category**: product or library names only in `tools` | Stops "aws" from appearing twice |
| **Read the whole text**, including "nice to have" sections and "or" lists | `"AWS, Azure or GCP"` gives 3 items, not 1 |

`experience_requirements` is the exception: it stays as short phrases like `"4+ years in data analysis"`, because splitting those would lose their meaning.

**Few-shot prompting.** Instead of only *describing* what we want, we also *show* one example inside the prompt:

```
JD text: "Strong stakeholder management and communication skills. Expert in SQL (joins, CTEs)
and building Tableau dashboards. 3+ years of experience."
Output:
{"technical_skills": ["sql", "joins", "ctes", "dashboards"],
 "soft_skills": ["stakeholder management", "communication"],
 "tools": ["tableau"],
 "experience_requirements": ["3+ years of experience"]}
```

- **Zero-shot** = instructions only. **One-shot / few-shot** = instructions plus 1 or a few worked examples.
- Examples work like showing a new colleague one finished form before they fill in 100 more. It's often clearer than any rule.
- **Risk:** the model might copy skills from the example into its answer, which would break our "never invent" rule. So the prompt says: *"only to show the format; never copy these skills unless they appear in the JD."*

**Result (tested on our 597-word JD):** every item is now 1–3 words. A short JD containing *"strong stakeholder management and communication skills… SQL queries using joins and window functions, build dashboards, and maintain data pipelines"* now correctly returns `stakeholder management`, `communication`, `sql`, `joins`, `window functions`, `dashboards`, `data pipelines`.

**Limits:**
- With `gpt-oss-20b`, the "one category only" rule is followed inconsistently: some runs still list e.g. `pandas` under both technical skills and tools. The larger `openai/gpt-oss-120b` (set `GROQ_MODEL` in `.env`) followed every rule in our tests. This is a good lesson: **a better prompt helps, but a small model can only follow so many rules at once.**
- Some differences from spaCy are just **naming** (`airflow` vs `apache airflow`, `rag` vs `retrieval-augmented generation`), not real misses. The exact-match comparison can't tell that these are the same skill.

### Precision vs recall: fixing over-extraction
After the "include techniques and concepts" rule, the model started **over-extracting**. On a long Business Analyst JD it returned 39 "technical skills", including:

- **Non-skills:** `comparison`, `saas`, `b2b`, `technology businesses`, `ai`
- **Near-duplicates:** `forecasts` *and* `forecasting`, `structured analyses` *and* `structured analysis`
- **Wrong category:** `attention to detail` (a soft skill) in the technical list

This is the classic trade-off between **precision** and **recall**:

| | Question it answers | Bad when… | Our example |
|---|---|---|---|
| **Precision** | "Of what you found, how much is *actually* a skill?" | You return junk | `saas`, `b2b` and `comparison` lower precision |
| **Recall** | "Of the real skills in the JD, how many did you find?" | You miss things | Missing `joins` or `window functions` lowers recall |

A simple way to remember it: think of fishing with a net.
- **Small net** (strict prompt): only good fish, but you miss many. **High precision, low recall.**
- **Huge net** (loose prompt): you catch every fish, plus old boots and seaweed. **High recall, low precision.**

```
precision = correct skills found / everything found
recall    = correct skills found / all real skills in the JD
```

Example: the JD has 20 real skills. The model returns 39 items, of which 19 are real.
→ precision = 19/39 ≈ **49%** (half is junk), recall = 19/20 = **95%** (it almost never misses).
Our earlier fix pushed recall up; now we need precision back **without** losing recall.

**What we changed (two layers):**

1. **The prompt now says what NOT to extract**, not just what to extract:
   - Business domains, industries and business models (`saas`, `b2b`, `fintech`, `collections`)
   - Company descriptions and the company's own product names
   - Job duties and vague words (`comparison`, `reports`, a bare `ai`)
   - Soft skills **never** go in `technical_skills`
   - Merge word-form variants into one name (`forecasts` + `forecasting` → `forecasting`)
   - Real techniques like `joins`, `window functions` and `dashboards` are **still kept**, to protect recall
   - The few-shot example now also shows an **exclusion**: the JD text contains "B2B SaaS", and the example says *"Left out on purpose: b2b and saas (business model, not a skill)"*. Showing a "don't" works better than only describing it.

2. **A Python safety net after the LLM:** `deduplicate_skills()` (now in `skill_cleanup.py`):
   - Lowercases each skill and makes the **last word singular** where it's safe: `dashboards` → `dashboard`, `queries` → `query`, `analyses` → `analysis`.
   - Two items with the same result count as the same skill; the first one is kept.
   - Short words (`aws`, `css`, `sas`) and words ending in "ss" (`process`) are **not** changed, because cutting their final "s" would change their meaning.
   - It also works **across** categories: if the same skill is in both soft skills and technical skills, soft skills wins; if it's in tools and technical skills, tools wins.

   Why both layers? The **prompt** handles things that need *understanding* (`forecasts` vs `forecasting`, or "is SaaS a skill?"). The **code** handles simple, mechanical cases *100% reliably*. LLMs follow rules most of the time, and code follows them every time.

**Results (live tests, 2 runs each, `gpt-oss-20b`):**

| JD | Before (total skills) | After (total skills) | Duplicates after | Domain words after |
|---|---|---|---|---|
| 597-word Senior Data Analyst JD | 60 and 75 (unstable) | 63 and 63 (stable) | none | none |
| Short Collections-style JD with SaaS/B2B/fintech | 16 | 17 | none | none (`ai` still slips through) |

In the second JD, `saas`, `b2b`, `fintech`, `technology businesses` and `comparisons` were all left out. `forecasts` was merged into `forecasting`, and `structured analyses` became `structured analysis`, while `joins`, `window functions` and `cohort analysis` were kept. One leftover: the model still returned a bare `ai` despite the rule. No prompt is perfect, which is why we measure.

### Cleaning up after the LLM: 4 code fixes
Even with a good prompt, a long KiteFishAI-style JD still showed 4 problems. Each one got a small, **predictable** Python fix.

**1. Near-duplicates → a canonical-name map (alias map)**
The model returned both `forecasts` and `forecasting`, and both `statistical models` and `statistical modeling`. Our plural rule can't catch these, because "forecasting" isn't the plural of "forecast". So `skills_list.py` now has a small dictionary:

```python
SKILL_ALIASES = {
    "forecast": "forecasting",                       # also covers "forecasts"
    "statistical model": "statistical modeling",     # also covers "statistical models"
    "dashboard building": "dashboards",
    "ms excel": "Excel",
    ...
}
```

Every LLM skill is looked up in it (plural forms too), and replaced by its **standard name**. After that, the duplicate check sees two identical names and keeps one. This is called **normalization** or **canonicalization**: many spellings, one official name. The standard names match the spellings in `SKILLS`, so the spaCy vs LLM comparison lines up better.

*Limit:* it only knows the variants we wrote down. A new variant needs one new line in `SKILL_ALIASES`.

**2. Long soft skills → prompt rule + a 4-word check**
The model returned sentences such as *"connecting quantitative analysis with business decisions"*. Two layers fix this:
- **Prompt:** every item, soft skills included, must be a 1–3 word skill **name**, with examples: that phrase → `business acumen`; *"working with incomplete, messy information"* → `ambiguity handling`.
- **Code:** `drop_long_phrases()` removes anything over **4 words**. We allow one extra word, so a real 4-word skill isn't lost. Removed phrases aren't hidden: the app lists them under the LLM column ("Removed (too long to be a skill name)"), so you can see what the rule did.

**3. Wrong categories → `skills_list.py` decides**
The model put `looker`, `tensorflow` and `pytorch` in technical skills, and sometimes `python` and `sql` in **tools**, while spaCy has them in Technical Skills. Two extractors disagreeing about categories makes the comparison confusing.

`apply_known_categories()` fixes this with a **single source of truth**: every skill that is in `skills_list.py` goes into the category it has there, no matter where the model put it.

```python
KNOWN_CATEGORY = {"python": "technical_skills", "sql": "technical_skills",
                  "tableau": "tools", "communication": "soft_skills", ...}   # built from SKILLS
```

spaCy reads `SKILLS` directly, and the LLM's answer is corrected to match it, so both columns always agree. Programming and query languages (Python, SQL, R) are in Technical Skills in `skills_list.py`, so that's where they end up. To change a skill's category for **both** extractors, you change **one line** in `skills_list.py`.

*Limit:* only skills in our list are corrected. A skill we never listed (like `prophet`) stays wherever the model put it.

**3b. "presentation skills" vs "presentation" → strip the word "skills"**
spaCy's list has `presentation skills`, but the LLM often writes just `presentation`, so the comparison called them different. Now a trailing "skill"/"skills" is removed before comparing (`comparison_key()` in `skill_cleanup.py`), and `app.py` uses that **same function for both spaCy and LLM results**. Soft skills from the LLM are also renamed (`"communication skills"` → `"communication"`). A single word like "skills" is left alone, so a name never becomes empty.

**Results (live, after these two fixes):** on two long JDs, 6 skills that both extractors found had **different** categories before cleanup (for example `python` in the LLM's tools, `pandas` in its technical skills). After cleanup there were **0**. A JD with "presentation skills" now shows `presentation` under "Both found" instead of once in each "only" list.

**4. Skipping the "About the company" section (spaCy)**
spaCy found `large language models` in *"KiteFishAI builds large language models…"*. That describes the **company's product**, not what the **candidate** needs. PhraseMatcher can't tell the difference: it matches words, not meaning.

The fix is simple **heading detection** in `classical_extractor.py`:
1. Find a company heading: a short line like `About Us`, `About the company`, `About KiteFishAI`, `Who we are`, or the inline form `About the company: We are…`.
2. Remove everything from there to the **next heading**. A heading is a short line (1–6 words) that isn't a bullet and doesn't end with a full stop.
3. Search only what's left.

```
About KiteFishAI                          <- company heading: start skipping
KiteFishAI builds large language models…  <- skipped

About the role                            <- next heading: stop skipping ("About the role" is kept)
You will write SQL…                       <- searched
```

**Limitations (be honest about these in interviews):**
- **It's a guess based on formatting.** If the JD is one big paragraph with no headings, nothing is skipped.
- **A company section with no heading after it:** only its first paragraph is removed, so we never throw away the whole JD by mistake.
- **A short line inside the company text** (like `Bengaluru, India`) looks like a heading, so skipping can stop early. Some company text then still gets searched. This fails *safe*: we may keep too much, but never remove the requirements.
- **Company info outside that section** (e.g. "our team uses Kubernetes" inside the responsibilities) is still matched.
- **Only spaCy skips it.** The LLM reads the whole JD, because it *can* understand context, and the prompt tells it to ignore company descriptions.

**Results on a 498-word KiteFishAI-style JD** (2 live runs, identical model output both times):

| | Model output | After cleanup |
|---|---|---|
| Technical skills | 32 | **17** |
| Tools also listed in technical skills | 11 (looker, tensorflow, pytorch, …) | **0** |
| Near-duplicate pairs | 15 | **0** |
| Items over 4 words | 0 (the new prompt rule worked) | 0 |
| spaCy skills | 31 (incl. `large language models`, `Docker` from the About section) | **29** |

### Temperature and consistency
`temperature` controls how "random" the model's word choices are. `0` means "always pick the most likely next word", so we use `temperature=0` to get **the same answer for the same JD** as often as possible.

It's not a 100% guarantee: reasoning models like gpt-oss can still vary a little between calls (in our tests, the same JD once gave 43 skills and another time 40). That's another reason the cleanup is in **code**: code gives the same result every time.

### Environment variables and `.env`
An **environment variable** is a named value stored outside your code, such as `GROQ_API_KEY=abc123`.

- Your `.env` file holds: `GROQ_API_KEY=abc123`
- `load_dotenv()` reads that file into the environment.
- `os.getenv("GROQ_API_KEY")` reads the value in Python.

**Why?** If you put the key inside `app.py` and push it to GitHub, anyone could steal it and use your quota. With `.env` + `.gitignore`, the key stays on your computer only.

### Streamlit session flow
Streamlit's key idea: **every time you interact with the page, the whole `app.py` runs again from top to bottom.**

```python
text = st.text_area("JD")          # runs every time
if st.button("Extract Skills"):    # True only on the run right after the click
    st.write("Extracting...")
```

- When you type, the script reruns, but the button is `False`, so nothing is extracted.
- When you click, the script reruns, the button is `True`, and the extraction code runs.
- `st.stop()` ends the current run early. We use it when the text is empty.
- `st.columns(2)` makes side-by-side areas. Anything inside `with col:` is drawn in that column.

---

## 6. Classical NLP vs LLM

### Why do they give different results?

| | spaCy PhraseMatcher | LLM (Groq) |
|---|---|---|
| How it "decides" | Exact match against a fixed list | Reads and "understands" the text |
| Finds skills not in our list? | ❌ Never | ✅ Yes (for example "dbt", "Looker Studio") |
| Understands synonyms? | ❌ "ML" ≠ "machine learning" | ✅ Usually |
| Same input → same output? | ✅ Always | ⚠️ Mostly (we use `temperature=0` to help) |
| Can make things up? | ❌ No | ⚠️ Possible, so the prompt says "never invent" |
| False matches | ⚠️ "R" might match the letter R in "R&D" | Fewer, because it uses context |
| Speed | ⚡ Milliseconds | 🐢 About 1–3 seconds (network + model) |
| Cost / internet | Free, offline | Needs an API key and internet |
| Extracts experience requirements? | ❌ Not built for it | ✅ Yes |
| Explainable? | ✅ "It matched this word in the list" | ❌ Hard to say exactly why |

### Example of a difference
JD text: *"Comfortable building dashboards in Looker Studio and writing dbt models."*
- spaCy finds **Looker** (from our list) but not "dbt", which isn't listed.
- The LLM finds **Looker Studio** and **dbt**.
- The comparison shows both "looker" (only spaCy) and "looker studio" (only LLM), even though they mean almost the same thing. Exact string comparison is a known limitation.

### When to use which?
- **Classical:** when you need speed, zero cost, privacy (no data leaves your machine), or results you can fully explain and repeat.
- **LLM:** when the text is messy, the vocabulary is open-ended, or you need understanding (like "2+ years of experience").
- **In real projects** people often **combine** them. For example, they use the LLM to discover new skills and add them to the list, or use the list to double-check the LLM's answers.

---

## 7. Deployment (Streamlit Community Cloud)

Running `streamlit run app.py` only works on **your** computer. To get a public link that anyone can open, we deploy to **Streamlit Community Cloud**, a free hosting service from the makers of Streamlit.

### How it works, in one picture

```
Your laptop ──git push──▶ GitHub (public code, NO key) ──▶ Streamlit Cloud (runs app.py)
                                                                 ▲
                                          Secrets box (your key) ┘  typed in by you, only here
```

1. Your code lives in a **GitHub repository** (a project folder online).
2. Streamlit Cloud **reads the code from GitHub**, installs `requirements.txt`, and runs `app.py` on its own server.
3. When you `git push` a change, the app **updates by itself**.
4. A free app **sleeps** after a while with no visitors. The next visitor clicks "wake up", which takes about a minute.

### What are secrets?
A **secret** is a value your app needs but that must stay private, like a password or an **API key**.

The problem: our repo is **public**, so anyone on the internet can read every file in it. If the Groq key were in the code, anyone could copy it and use your account and free quota. Bots scan GitHub for leaked keys all day, often within minutes of a push.

The solution: keep the key **out of the code** and give it to each place the app runs **separately**:

| Where the app runs | Where the key lives | How it gets uploaded |
|---|---|---|
| Your laptop | `.env` file | It doesn't: `.gitignore` blocks it |
| Streamlit Cloud | App settings → **Secrets** box | Typed into the website by you, stored privately |
| GitHub | **Nowhere** | — |

You type the secret in **TOML** format (simple `name = "value"` lines):

```toml
GROQ_API_KEY = "gsk_your_real_key"
GROQ_MODEL = "openai/gpt-oss-120b"   # optional
```

### Why didn't the code need to change?
Streamlit Cloud saves those lines as a private `secrets.toml` file. When the app starts, Streamlit **also copies every top-level secret into the environment variables**. Our code already reads environment variables:

```python
load_dotenv()                              # on the cloud: no .env file, so this quietly does nothing
os.getenv("GROQ_API_KEY")                  # finds the secret
os.getenv("GROQ_MODEL") or DEFAULT_MODEL   # finds the optional model, or uses the default
```

Same code, two places:
- **Laptop:** `.env` → `load_dotenv()` → environment variables → `os.getenv`
- **Cloud:** Secrets box → Streamlit → environment variables → `os.getenv`

This is a common pattern in real projects: **configuration comes from the environment, not from the code**. (`st.secrets["GROQ_API_KEY"]` would also work, but only inside Streamlit. `os.getenv` works everywhere.)

### Two safety nets for the key
1. **`.gitignore`** lists `.env` and `.streamlit/secrets.toml`, so `git add .` skips them.
2. **Check before every commit:** run `git status` and make sure `.env` is **not** in the list.

If a key ever does get pushed, deleting the file isn't enough, because Git keeps history. **Revoke the key** at https://console.groq.com/keys and create a new one.

### Why pin versions?
`requirements.txt` says `streamlit==1.63.0`, not just `streamlit`. Without pins, every deploy installs the *newest* versions, and one day an update could break the app without you changing anything. Pinned versions mean the cloud uses exactly the setup we tested.

⚠️ **Public app = shared quota:** anyone who opens your app link can click "Extract Skills", and each click uses **your** Groq free quota. They can't *see* the key, but they can *spend* it.
