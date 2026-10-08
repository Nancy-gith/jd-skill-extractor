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


# "About ..." headings that describe the JOB, not the company. These are kept.
ABOUT_THE_JOB = ("the role", "this role", "the job", "this job", "the position",
                 "the opportunity", "you", "the team")

# Other headings that introduce a company description.
COMPANY_HEADINGS = ("who we are", "company overview", "our company", "our story")


def heading_text(line: str) -> str:
    """Clean a line so headings are easy to compare: "## About Us:" -> "about us"."""
    return line.strip().strip("#*_ ").rstrip(":").strip().lower()


def is_heading(line: str) -> bool:
    """Guess whether a line is a section heading.

    A heading is short (1-6 words), isn't a bullet point, and doesn't end
    like a sentence. Examples: "Responsibilities", "What you'll do:", "About Us".
    """
    stripped = line.strip()
    if not stripped:
        return False
    if stripped[0] in "-•*" and not stripped.startswith("**"):   # bullet, not **bold**
        return False
    if stripped.endswith((".", ",", ";")):
        return False
    return 1 <= len(heading_text(line).split()) <= 6


def is_company_heading(line: str) -> bool:
    """True for "About Us", "About the company", "About KiteFishAI", "Who we are"...

    Also matches the inline form "About the company: We are a...".
    "About the role" and "About you" are NOT company headings (see ABOUT_THE_JOB).
    """
    # "About the company: We are..." -> title "about the company", inline text "We are..."
    before_colon, _, inline_text = line.partition(":")
    if not inline_text.strip() and not is_heading(line):
        return False                 # a normal sentence, e.g. "About 50% of the role is SQL."
    title = heading_text(before_colon)
    if len(title.split()) > 6:
        return False                 # too long to be a heading
    if title.startswith("about "):
        return not title.removeprefix("about ").startswith(ABOUT_THE_JOB)
    return title in COMPANY_HEADINGS


def remove_about_section(text: str) -> tuple[str, str]:
    """Remove the "About the company" section, if the JD has one.

    Returns (text_to_search, removed_text).

    Rules (simple on purpose):
    - The section starts at a company heading (see is_company_heading).
    - It ends at the next heading, e.g. "Responsibilities".
    - If no heading follows, only the first paragraph (up to a blank line)
      is removed, so we never accidentally throw away the whole JD.
    """
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if not is_company_heading(line):
            continue

        # Find where the section ends.
        end = None
        for i in range(start + 1, len(lines)):
            if is_heading(lines[i]):
                end = i
                break
        if end is None:
            # No heading after it: remove only the first paragraph.
            end = start + 1
            has_inline_text = bool(line.partition(":")[2].strip())
            if not has_inline_text:
                # Stand-alone heading: skip blank lines to reach its paragraph.
                while end < len(lines) and not lines[end].strip():
                    end += 1
            while end < len(lines) and lines[end].strip():   # the paragraph itself
                end += 1

        kept = lines[:start] + lines[end:]
        removed = lines[start:end]
        return "\n".join(kept), "\n".join(removed)

    return text, ""   # no company section found


def extract_skills_classical(text: str) -> dict[str, list[str]]:
    """Find known skills in `text` and group them by category.

    Input:  the job description as a string.
    Output: {"Technical Skills": [...], "Soft Skills": [...], "Tools": [...]}
            Each list is sorted and has no duplicates.
    The "About the company" section is skipped, because tools the company
    uses or sells are not requirements for the candidate.
    """
    # Start with an empty set for every category (sets remove duplicates).
    results: dict[str, set[str]] = {category: set() for category in SKILLS}

    text, _removed = remove_about_section(text)
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
