"""
classical_extractor.py
----------------------
Extracts skills from a job description using classical NLP (spaCy).

How it works, in short:
1. Split the text into tokens (words and punctuation) with spaCy.
2. Use a PhraseMatcher to find every phrase from our hand-written SKILLS list.
3. Group the matches into categories (Technical Skills, Soft Skills, Tools).

No AI model and no internet are needed. It is fast and predictable,
but it can only find skills that already exist in skills_list.py.
"""

import spacy
from spacy.matcher import PhraseMatcher

from skills_list import SKILLS

# spacy.blank("en") gives us an English tokenizer only (no trained model).
# That is all PhraseMatcher needs, so we skip downloading a large model.
nlp = spacy.blank("en")


def build_matcher() -> PhraseMatcher:
    """Create a PhraseMatcher loaded with every skill from SKILLS.

    attr="LOWER" means we compare the lowercase form of each token,
    so "PYTHON", "Python" and "python" all match.
    """
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    for category, skills in SKILLS.items():
        # nlp.make_doc() only tokenizes, which is faster than running nlp().
        patterns = [nlp.make_doc(skill) for skill in skills]
        # The category name becomes the "label" of these patterns.
        matcher.add(category, patterns)

    return matcher


# Build the matcher once when the file is imported, not on every call.
matcher = build_matcher()

def normalize(skill: str) -> str:
    """Lowercase and treat hyphens as spaces: "Problem-Solving" -> "problem solving"."""
    return skill.lower().replace("-", " ")


# Lookup table: normalized skill -> the spelling used in SKILLS.
# Used so "power bi" in the JD is shown as "Power BI" in the results,
# and so "problem-solving" and "problem solving" count as one skill.
CANONICAL_NAMES: dict[str, str] = {}
for skills in SKILLS.values():
    for skill in skills:
        # setdefault keeps the FIRST spelling we see for each normalized name.
        CANONICAL_NAMES.setdefault(normalize(skill), skill)


def extract_skills_classical(text: str) -> dict[str, list[str]]:
    """Find known skills in `text` and group them by category.

    Input:  the job description as a string.
    Output: {"Technical Skills": [...], "Soft Skills": [...], "Tools": [...]}
            Each list is sorted and has no duplicates.
    """
    # Start with an empty set for every category (sets remove duplicates).
    results: dict[str, set[str]] = {category: set() for category in SKILLS}

    doc = nlp(text)

    # Each match is (match_id, start_token, end_token).
    for match_id, start, end in matcher(doc):
        category = nlp.vocab.strings[match_id]  # turn the ID back into a label
        matched_text = doc[start:end].text
        # Show the clean spelling from our list instead of the JD's spelling.
        skill = CANONICAL_NAMES.get(normalize(matched_text), matched_text)
        results[category].add(skill)

    # Convert sets to sorted lists so the output is tidy and stable.
    return {category: sorted(skills, key=str.lower) for category, skills in results.items()}
