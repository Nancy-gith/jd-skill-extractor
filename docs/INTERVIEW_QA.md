# Interview Q&A

13 questions you might be asked about this project, with simple answers you can say out loud.

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

### 6. How do you get reliable JSON from the LLM, and why do you still use try/except?
"I use Groq's structured outputs: I pass a JSON Schema that says the reply must have exactly four keys, each a list of strings, and with strict mode the API enforces that shape. That's a step up from plain JSON mode, which only guarantees *some* valid JSON. Because gpt-oss is a reasoning model, I also give it enough output tokens and set reasoning effort to low, so its hidden thinking doesn't use up the budget before the JSON is written. If validation still fails, the app retries once. I still wrap `json.loads` in try/except because you should never fully trust outside data. The reply might be cut off, or the model might return the wrong structure. I also check that all four keys exist and that each one is a list, and fill in empty lists if not. So one bad response never crashes the app."

### 7. How do you handle the API key securely?
"The key lives in a `.env` file, which `python-dotenv` loads into environment variables, and I read it with `os.getenv`. The key is never written in the code. `.env` is in `.gitignore`, so it never gets pushed to GitHub. I commit a `.env.example` file instead, so others know which variable they need. If the key is missing, the app shows a clear message instead of crashing."

### 8. How does Streamlit work, and how did you structure the UI?
"Streamlit reruns the whole script from top to bottom every time the user interacts. `st.button` returns True only on the run right after it's clicked, so the extraction happens inside that `if` block. I check for empty input first and use `st.stop()` to end early. Then I use `st.columns(2)` for the side-by-side view. I kept all the logic in separate files, so `app.py` only handles display."

### 9. How does the comparison section work?
"I flatten each result into a Python set of normalized skill names, meaning lowercase with hyphens turned into spaces. Then I use set operations: `llm - spacy` gives skills only the LLM found, `spacy - llm` gives skills only spaCy found, and `spacy & llm` gives skills both found. Sets make this simple and fast, and they remove duplicates automatically."

### 10. What would you improve next?
"A few things. One, semantic matching with embeddings. Right now a hand-written alias map merges known variants like 'forecasts' and 'forecasting', but embeddings would also catch variants I never listed, like 'Looker' and 'Looker Studio'. Two, verify each LLM skill against the text to catch hallucinations. Three, cache LLM results with `st.cache_data` so the same job description doesn't cost another API call. Four, add unit tests for the extractors. Five, let users upload a PDF and compare the job description against their resume to find skill gaps."

### 11. The LLM output was messy. How did you clean it up?
"I saw four kinds of mistakes, and I fixed them in two layers. In the prompt, I added rules: one category per skill, skill names of 1 to 3 words, and an example showing a long phrase turned into a short name like 'ambiguity handling'. But a prompt is followed most of the time, not every time, so I added a small Python cleanup step after the API call. It drops anything over 4 words and lists it in the UI, so nothing disappears silently. It maps variants like 'forecasts' or 'statistical models' to one standard name with an alias dictionary. It moves known tools like TensorFlow from technical skills into tools, using the same tools list spaCy uses. And it removes duplicates. On a long test JD, that took technical skills from 32 down to 17, with zero duplicates. The principle is: use the LLM for understanding, and use code for rules that must hold every time."

### 12. spaCy picked up skills from the company description. How did you handle that?
"PhraseMatcher matches words, not meaning, so 'KiteFishAI builds large language models' counted as a skill requirement. I added simple heading detection: if the JD has a section like 'About us' or 'About KiteFishAI', the classical extractor skips everything up to the next heading. 'About the role' and 'About you' are kept, because they describe the job. It's deliberately simple, and it has limits. It depends on the JD having headings, and if there's no next heading it only removes one paragraph, so it can never delete the requirements by mistake. The app also shows which section was skipped, so the user can see it."

### 13. What are precision and recall, and how did they apply here?
"Precision is: of everything I extracted, how much is actually a skill. Recall is: of all the real skills in the JD, how many I found. When I first told the LLM to include techniques, recall went up, but it also started returning things like 'SaaS' and 'B2B', so precision dropped. I fixed precision without losing recall by adding an explicit exclude list to the prompt, plus the cleanup code. I measured it with before-and-after counts on real JDs instead of just eyeballing it. It's the same trade-off as a fishing net: too small and you miss fish, too big and you catch boots."
