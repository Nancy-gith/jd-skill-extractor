"""
skill_cleanup.py
----------------
Cleans up the LLM's skill lists with plain Python rules, after the API call.

Why? A prompt tells the model what we want, and it follows it MOST of the time.
These rules fix the common slips EVERY time, in 5 steps:

1. drop_long_phrases()       "working with incomplete messy information" -> removed
2. apply_aliases()           "forecasts" -> "forecasting"
3. apply_known_categories()  "python" in tools -> technical_skills (skills_list.py decides)
4. strip_soft_suffixes()     "presentation skills" -> "presentation"
5. deduplicate_skills()      "dashboards" + "Dashboard" -> one item
"""

from skills_list import SKILL_ALIASES, SKILLS

# The 3 lists that hold skills. experience_requirements holds phrases
# like "4+ years in data analysis", so the cleanup steps leave it alone.
SKILL_CATEGORIES = ["technical_skills", "soft_skills", "tools"]

# The prompt asks for 1-3 words. We allow 4 so that real skills like
# "large language model evaluation" aren't lost, and drop anything longer.
MAX_SKILL_WORDS = 4

# Order used when the same skill appears in more than one category:
# the FIRST category listed here keeps it. Soft skills come first so that
# "attention to detail" stays a soft skill; brand names stay in tools.
DEDUPE_PRIORITY = ["soft_skills", "tools", "technical_skills"]


def lookup_key(skill: str) -> str:
    """Lowercase, treat hyphens as spaces, tidy spaces: "Time-Series " -> "time series"."""
    return " ".join(skill.lower().replace("-", " ").split())


def strip_skill_suffix(skill: str) -> str:
    """Remove a trailing "skill"/"skills": "presentation skills" -> "presentation".

    A single word is left alone, so "skills" never becomes an empty string.
    """
    words = skill.split()
    if len(words) > 1 and words[-1].lower() in ("skill", "skills"):
        return " ".join(words[:-1])
    return skill


def comparison_key(skill: str) -> str:
    """The form used to compare skills: lowercase, no hyphens, no trailing "skills".

    app.py uses this for BOTH spaCy and LLM results, so
    "Presentation Skills" (spaCy) and "presentation" (LLM) count as the same skill.
    """
    return lookup_key(strip_skill_suffix(skill))


def singular_forms(word: str) -> set[str]:
    """Return possible singular forms of `word`, used only to spot duplicates.

    "dashboards" -> {"dashboard"}, "queries" -> {"query"},
    "analyses" -> {"analyse", "analys", "analysis"}.
    Short words (aws, css, sas) and words ending in "ss" (process) are left
    alone, because removing their final "s" would change their meaning.
    """
    if len(word) <= 3 or not word.endswith("s") or word.endswith("ss"):
        return set()
    forms = {word[:-1]}                      # dashboards -> dashboard
    if word.endswith("ies"):
        forms.add(word[:-3] + "y")           # queries -> query
    if word.endswith("es"):
        forms.add(word[:-2])                 # matches -> match
        forms.add(word[:-2] + "is")          # analyses -> analysis
    return forms


def duplicate_keys(skill: str) -> set[str]:
    """All the lookup keys that count as "the same skill" as `skill`.

    The key is the normalized name, plus versions where the LAST word is made
    singular: "Structured Analyses" -> {"structured analyses", "structured analysis", ...}.
    """
    name = comparison_key(skill)
    *first_words, last_word = name.split(" ")
    keys = {name}
    for form in singular_forms(last_word):
        keys.add(" ".join(first_words + [form]))
    return keys


# skills_list.py category names -> the LLM's JSON keys.
LIST_TO_LLM_CATEGORY = {
    "Technical Skills": "technical_skills",
    "Soft Skills": "soft_skills",
    "Tools": "tools",
}

# Every skill in skills_list.py -> the category it belongs to.
# {"python": "technical_skills", "sql": "technical_skills", "tableau": "tools", ...}
# This makes skills_list.py the single source of truth for categories:
# spaCy reads it directly, and the LLM's answers are corrected to match it.
KNOWN_CATEGORY: dict[str, str] = {
    comparison_key(skill): LIST_TO_LLM_CATEGORY[category]
    for category, skills in SKILLS.items()
    for skill in skills
}


# ---------- Step 1 ----------
def drop_long_phrases(result: dict[str, list[str]]) -> tuple[dict[str, list[str]], list[str]]:
    """Remove items longer than MAX_SKILL_WORDS words: they are sentences, not skill names.

    Returns the cleaned result AND the removed phrases, so the app can show
    what was dropped instead of hiding it.
    """
    cleaned = dict(result)
    removed: list[str] = []
    for category in SKILL_CATEGORIES:
        kept = []
        for skill in result[category]:
            if len(skill.split()) > MAX_SKILL_WORDS:
                removed.append(skill)
            else:
                kept.append(skill)
        cleaned[category] = kept
    return cleaned, removed


# ---------- Step 2 ----------
def canonical_name(skill: str) -> str:
    """Return the standard name from SKILL_ALIASES, or the skill unchanged.

    Plural forms are checked too, so "forecasts" finds the "forecast" entry.
    """
    for key in duplicate_keys(skill):
        if key in SKILL_ALIASES:
            return SKILL_ALIASES[key]
    return skill


def apply_aliases(result: dict[str, list[str]]) -> dict[str, list[str]]:
    """Replace every skill with its standard name: "statistical models" -> "statistical modeling"."""
    cleaned = dict(result)
    for category in SKILL_CATEGORIES:
        cleaned[category] = [canonical_name(skill) for skill in result[category]]
    return cleaned


# ---------- Step 3 ----------
def known_category(skill: str) -> str | None:
    """Return the category skills_list.py gives this skill, or None if it isn't listed.

    Plural forms and a trailing "skills" are ignored: "Tableau dashboards" isn't
    listed, but "Python" -> "technical_skills" and "presentation skills" -> "soft_skills".
    """
    for key in duplicate_keys(skill):
        if key in KNOWN_CATEGORY:
            return KNOWN_CATEGORY[key]
    return None


def apply_known_categories(result: dict[str, list[str]]) -> dict[str, list[str]]:
    """Put every skill that is in skills_list.py into the SAME category spaCy uses.

    e.g. the model puts "python" in tools -> moved to technical_skills,
    "tensorflow" in technical_skills -> moved to tools.
    Skills not in skills_list.py stay where the model put them.
    """
    cleaned: dict[str, list[str]] = {**result, **{category: [] for category in SKILL_CATEGORIES}}
    for category in SKILL_CATEGORIES:
        for skill in result[category]:
            right_category = known_category(skill) or category
            cleaned[right_category].append(skill)
    return cleaned


# ---------- Step 4 ----------
def strip_soft_suffixes(result: dict[str, list[str]]) -> dict[str, list[str]]:
    """Soft skills drop a trailing "skills": "communication skills" -> "communication"."""
    cleaned = dict(result)
    cleaned["soft_skills"] = [strip_skill_suffix(skill) for skill in result["soft_skills"]]
    return cleaned


# ---------- Step 5 ----------
def deduplicate_skills(result: dict[str, list[str]]) -> dict[str, list[str]]:
    """Remove duplicate skills inside and across categories.

    Two items are duplicates when they match after lowercasing, removing a
    trailing "skills", and making the last word singular, e.g. "Dashboards"
    and "dashboard". The first one seen
    is kept (categories are checked in DEDUPE_PRIORITY order).
    """
    seen: set[str] = set()
    cleaned = dict(result)
    for category in DEDUPE_PRIORITY:
        kept = []
        for skill in result[category]:
            keys = duplicate_keys(skill)
            if keys & seen:          # any shared key = already have this skill
                continue
            seen |= keys
            kept.append(skill)
        cleaned[category] = kept
    return cleaned


# ---------- All steps together ----------
def clean_llm_skills(result: dict[str, list[str]]) -> dict[str, list[str]]:
    """Run all 5 cleanup steps, in order.

    Input:  the parsed LLM result (technical_skills, soft_skills, tools,
            experience_requirements).
    Output: the same keys, cleaned, plus "removed_phrases": the long phrases
            dropped in step 1 (shown in the app so nothing disappears silently).
    """
    result, removed = drop_long_phrases(result)
    result = apply_aliases(result)            # before dedupe, so aliases can collapse
    result = apply_known_categories(result)   # same categories as spaCy
    result = strip_soft_suffixes(result)
    result = deduplicate_skills(result)
    result["removed_phrases"] = removed
    return result
