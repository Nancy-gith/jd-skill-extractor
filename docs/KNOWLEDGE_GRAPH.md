# Knowledge Graph

Visual maps of the project. GitHub and VS Code (with a Mermaid extension) render these diagrams automatically.

---

## 1. Data-flow diagram

How a job description moves through the app.

```mermaid
flowchart TD
    U([User pastes JD and clicks Extract Skills]) --> A[app.py]
    A -->|empty text?| W[/Show warning and st.stop/]
    A -->|jd_text| C[classical_extractor.py<br/>extract_skills_classical]
    A -->|jd_text| L[llm_extractor.py<br/>extract_skills_llm]

    S[(skills_list.py<br/>SKILLS + SKILL_ALIASES)] --> C
    S --> CL
    C --> AB[remove_about_section<br/>skip 'About the company'] --> T[spaCy tokenizer] --> M[PhraseMatcher<br/>attr=LOWER] --> CR[Grouped skills:<br/>Technical / Soft / Tools]

    E[(.env<br/>GROQ_API_KEY)] --> L
    L --> G[Groq API<br/>structured outputs] --> P[parse_llm_json<br/>try/except] --> CL[skill_cleanup.py<br/>long phrases, aliases,<br/>categories, dedupe] --> LR[technical_skills, soft_skills,<br/>tools, experience_requirements]
    L -.->|missing key / API error / bad JSON| ERR[/LLMExtractionError shown in LLM column/]

    CR --> COL1[Left column: Classical spaCy]
    LR --> COL2[Right column: LLM Groq]
    CR --> CMP{Set comparison}
    LR --> CMP
    CMP --> O1[Only LLM found]
    CMP --> O2[Only spaCy found]
    CMP --> O3[Both found]
```

---

## 2. Concept map

How the ideas behind the project connect.

```mermaid
flowchart LR
    SE[Skill Extraction] --> NLP[Classical NLP]
    SE --> LLM[Large Language Model]

    NLP --> TOK[Tokenization] --> PM[PhraseMatcher]
    PM --> LOW[Case-insensitive<br/>attr=LOWER]
    PM --> LIST[Hand-written skills list]
    LIST --> LIM1[Limit: can only find<br/>what is listed]

    LLM --> API[API call over HTTP]
    API --> KEY[API key]
    KEY --> ENV[Environment variables<br/>.env + python-dotenv]
    ENV --> GIT[.gitignore keeps<br/>secrets safe]
    LLM --> PR[Prompt<br/>system + user messages]
    PR --> RULE[Rule: never invent skills]
    PR --> JM[JSON mode]
    JM --> JSON[JSON text]
    JSON --> PARSE[Parsing<br/>json.loads + try/except]
    PARSE --> VAL[Validation<br/>fill missing keys]
    LLM --> TEMP[temperature=0<br/>more consistent]

    PM --> OUT[Grouped skills]
    VAL --> CLEAN[Cleanup rules<br/>aliases, categories from skills_list, dedupe] --> OUT
    PM --> ABOUT[Heading detection<br/>skip company section]
    OUT --> SET[Python sets<br/>difference and intersection]
    SET --> CMP[Comparison]

    UI[Streamlit] --> RERUN[Script reruns<br/>on each interaction]
    UI --> BTN[st.button / st.columns / st.stop]
    UI --> CMP
```

---

## 3. File dependency map

Which file imports which. Arrows point from the importer to the file or package it imports.

```mermaid
flowchart TD
    APP[app.py] --> CE[classical_extractor.py]
    APP --> LE[llm_extractor.py]
    APP --> ST[(streamlit)]

    CE --> SL[skills_list.py]
    CE --> SP[(spacy)]

    LE --> SC[skill_cleanup.py]
    SC --> SL
    LE --> GR[(groq)]
    LE --> DE[(python-dotenv)]
    LE --> JS[(json, os<br/>standard library)]
    LE -.reads at runtime.-> ENVF[.env file]

    classDef pkg fill:#eef,stroke:#88a;
    class ST,SP,GR,DE,JS pkg;
```

Notes:
- `skills_list.py` imports nothing, because it is pure data. Both `classical_extractor.py` and `skill_cleanup.py` read it, so there is one source of truth for skills and tools.
- `classical_extractor.py` and `llm_extractor.py` don't know about each other or about Streamlit. They can be tested or reused on their own.
- Only `app.py` knows about the UI. This is called **separation of concerns**.
