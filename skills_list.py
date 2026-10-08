"""
skills_list.py
--------------
A hand-written list of common Data Analyst / AI skills, grouped by category.

The classical (spaCy) extractor can ONLY find skills that are in this list.
That is the main limitation of the rule-based approach: if a skill is not
written here, it will never be detected.
"""

# Each key is a category name shown in the UI.
# Each value is a list of skill phrases to search for (case does not matter).
SKILLS: dict[str, list[str]] = {
    "Technical Skills": [
        "Python",
        "SQL",
        "R",
        "statistics",
        "machine learning",
        "deep learning",
        "natural language processing",
        "NLP",
        "computer vision",
        "data analysis",
        "data visualization",
        "data cleaning",
        "data wrangling",
        "data modeling",
        "data mining",
        "ETL",
        "A/B testing",
        "hypothesis testing",
        "regression",
        "classification",
        "clustering",
        "time series",
        "forecasting",
        "feature engineering",
        "predictive modeling",
        "neural networks",
        "generative AI",
        "large language models",
        "LLM",
        "prompt engineering",
        "RAG",
        "web scraping",
        "API",
        "data warehousing",
        "cloud computing",
    ],
    "Soft Skills": [
        "communication",
        "problem solving",
        "problem-solving",
        "critical thinking",
        "teamwork",
        "collaboration",
        "stakeholder management",
        "attention to detail",
        "time management",
        "presentation skills",
        "storytelling",
        "leadership",
        "adaptability",
        "curiosity",
        "analytical thinking",
    ],
    "Tools": [
        "Excel",
        "Power BI",
        "Tableau",
        "Looker",
        "Google Sheets",
        "pandas",
        "NumPy",
        "Matplotlib",
        "Seaborn",
        "scikit-learn",
        "TensorFlow",
        "PyTorch",
        "Keras",
        "spaCy",
        "Hugging Face",
        "LangChain",
        "Jupyter",
        "Git",
        "GitHub",
        "Docker",
        "AWS",
        "Azure",
        "GCP",
        "Snowflake",
        "BigQuery",
        "MySQL",
        "PostgreSQL",
        "MongoDB",
        "Apache Spark",
        "Airflow",
        "Streamlit",
        "Jira",
    ],
}


# ---------------------------------------------------------------------------
# SKILL_ALIASES: different ways of writing the SAME skill -> one standard name.
#
# The LLM sometimes writes "forecasts" in one place and "forecasting" in
# another. skill_cleanup.py looks up every LLM skill here and replaces it with
# the standard name, so duplicates collapse into one item.
# Keys are lowercase. Plurals are handled automatically, so "forecast" also
# covers "forecasts", and "dashboard" also covers "dashboards".
# Standard names match the spellings in SKILLS where possible, so the
# spaCy vs LLM comparison lines up.
# ---------------------------------------------------------------------------
SKILL_ALIASES: dict[str, str] = {
    # forecasting
    "forecast": "forecasting",
    "forecast modeling": "forecasting",
    "forecasting model": "forecasting",
    # statistical modeling
    "statistical model": "statistical modeling",
    "statistical modelling": "statistical modeling",
    # dashboards
    "dashboard": "dashboards",
    "dashboarding": "dashboards",
    "dashboard building": "dashboards",
    "dashboard development": "dashboards",
    "dashboard design": "dashboards",
    # data visualization
    "data visualisation": "data visualization",
    "visualization": "data visualization",
    "visualisation": "data visualization",
    # data pipelines
    "data pipeline": "data pipelines",
    "pipeline": "data pipelines",
    # a/b testing
    "a/b test": "A/B testing",
    "ab test": "A/B testing",
    "ab testing": "A/B testing",
    "split testing": "A/B testing",
    # predictive modeling
    "predictive model": "predictive modeling",
    "predictive modelling": "predictive modeling",
    # exploratory data analysis
    "eda": "exploratory data analysis",
    "exploratory analysis": "exploratory data analysis",
    # data cleaning
    "data cleansing": "data cleaning",
    # query optimization
    "query performance tuning": "query optimization",
    "sql optimization": "query optimization",
    "sql performance tuning": "query optimization",
    # AI / LLMs
    "llm": "large language models",
    "large language model": "large language models",
    "genai": "generative AI",
    "gen ai": "generative AI",
    "retrieval augmented generation": "RAG",
    # machine learning
    "ml": "machine learning",
    "machine learning model": "machine learning",
    # storytelling
    "data storytelling": "storytelling",
    # communication
    "written communication": "communication",
    "verbal communication": "communication",
    "oral communication": "communication",
    "communication skills": "communication",
    # tools written in different ways
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "advanced excel": "Excel",
    "powerbi": "Power BI",
    "microsoft power bi": "Power BI",
    "sklearn": "scikit-learn",
}
