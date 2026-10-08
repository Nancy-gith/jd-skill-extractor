# Interview Q&A

10 questions you might be asked about this project, with simple answers you can say out loud.

---

### 1. Can you explain this project in 30 seconds?
"It's a Streamlit app that extracts skills from a job description in two ways. First, classical NLP: spaCy's PhraseMatcher searches for skills from a hand-written list of about 80 skills. Second, an LLM on the Groq API that reads the job description and returns structured JSON. The app shows both results side by side, plus a comparison of what each method found that the other missed. I built it to understand the trade-offs between rule-based NLP and LLMs."

### 2. What is spaCy's PhraseMatcher and why did you use it?
"PhraseMatcher finds exact phrases from a list inside a text. It works on tokens, so it handles multi-word skills like 'machine learning' or 'Power BI'. I set `attr="LOWER"` so matching ignores case. I used it because it's fast, free, works offline, and always gives the same answer, which makes it a good baseline to compare the LLM against."

### 3. What is tokenization?
"Tokenization means splitting text into small units called tokens, usually words and punctuation. For example, 'I know SQL.' becomes 'I', 'know', 'SQL', '.'. The PhraseMatcher compares tokens, so 'SQL,' with a comma still matches 'SQL'. I only needed the tokenizer, so I used `spacy.blank("en")` instead of downloading a full trained model."

### 4. Why do the two methods give different results?
"The PhraseMatcher can only find skills that are in my list, and only with the exact wording. The LLM understands context, so it can find skills I never listed, like 'dbt', and synonyms like 'ML'. It can also pull out experience requirements. On the other hand, the LLM is slower, needs internet and an API key, and could in theory invent a skill. The PhraseMatcher never invents anything."

### 5. How do you stop the LLM from making up skills?
"Three ways. First, the system prompt clearly says to extract only skills that are explicitly mentioned and never invent any. Second, I set `temperature=0` so the output is more focused and consistent. Third, the comparison with spaCy acts as a sanity check: if the LLM lists something, I can check the text. A further step would be to check that each LLM skill actually appears in the job description."

### 6. What is JSON mode and why do you still use try/except?
"JSON mode tells the API to return only valid JSON instead of free text, so my code can read it reliably. I still wrap `json.loads` in try/except because you should never fully trust outside data. The reply might be cut off, or the model might return the wrong structure. I also check that all four keys exist and that each one is a list, and fill in empty lists if not. So one bad response never crashes the app."

### 7. How do you handle the API key securely?
"The key lives in a `.env` file, which `python-dotenv` loads into environment variables, and I read it with `os.getenv`. The key is never written in the code. `.env` is in `.gitignore`, so it never gets pushed to GitHub. I commit a `.env.example` file instead, so others know which variable they need. If the key is missing, the app shows a clear message instead of crashing."

### 8. How does Streamlit work, and how did you structure the UI?
"Streamlit reruns the whole script from top to bottom every time the user interacts. `st.button` returns True only on the run right after it's clicked, so the extraction happens inside that `if` block. I check for empty input first and use `st.stop()` to end early. Then I use `st.columns(2)` for the side-by-side view. I kept all the logic in separate files, so `app.py` only handles display."

### 9. How does the comparison section work?
"I flatten each result into a Python set of normalized skill names, meaning lowercase with hyphens turned into spaces. Then I use set operations: `llm - spacy` gives skills only the LLM found, `spacy - llm` gives skills only spaCy found, and `spacy & llm` gives skills both found. Sets make this simple and fast, and they remove duplicates automatically."

### 10. What would you improve next?
"A few things. One, fuzzy or semantic matching, for example with embeddings, so 'Looker' and 'Looker Studio' or 'ML' and 'machine learning' count as the same skill. Two, verify each LLM skill against the text to catch hallucinations. Three, cache LLM results with `st.cache_data` so the same job description doesn't cost another API call. Four, add unit tests for the extractors. Five, let users upload a PDF and compare the job description against their resume to find skill gaps."
