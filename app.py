"""
app.py
------
The Streamlit user interface for JD Skill Extractor.

Run it with:  streamlit run app.py

Flow: paste a job description -> click "Extract Skills" ->
see spaCy results and LLM results side by side -> see a comparison.
"""

import streamlit as st

from classical_extractor import extract_skills_classical, normalize
from llm_extractor import LLMExtractionError, extract_skills_llm

# Map the LLM's JSON keys to the same category names spaCy uses,
# so both columns look the same and are easy to compare.
LLM_KEY_TO_CATEGORY: dict[str, str] = {
    "technical_skills": "Technical Skills",
    "soft_skills": "Soft Skills",
    "tools": "Tools",
}


def show_skill_groups(groups: dict[str, list[str]]) -> None:
    """Display each category as a heading with its skills listed below it."""
    for category, skills in groups.items():
        st.markdown(f"**{category}** ({len(skills)})")
        if skills:
            st.write(", ".join(skills))
        else:
            st.caption("None found")


def all_skills_normalized(groups: dict[str, list[str]]) -> set[str]:
    """Flatten all categories into one set of normalized skills, for comparing."""
    return {normalize(skill) for skills in groups.values() for skill in skills}


# ---------- Page layout ----------
st.set_page_config(page_title="JD Skill Extractor", layout="wide")
st.title("JD Skill Extractor")
st.write("Paste a job description to compare classical NLP (spaCy) with an LLM (Groq).")

jd_text = st.text_area("Job description", height=250, placeholder="Paste the job description here...")

# Streamlit re-runs this whole file from top to bottom on every interaction.
# st.button() returns True only on the run right after it was clicked.
if st.button("Extract Skills", type="primary"):
    if not jd_text.strip():
        st.warning("Please paste a job description first.")
        st.stop()  # stop this run here; nothing below is drawn

    col_classical, col_llm = st.columns(2)

    # ----- Left column: classical NLP -----
    with col_classical:
        st.subheader("Classical (spaCy)")
        classical_result = extract_skills_classical(jd_text)
        show_skill_groups(classical_result)

    # ----- Right column: LLM -----
    llm_groups: dict[str, list[str]] | None = None
    with col_llm:
        st.subheader("LLM (Groq)")
        try:
            with st.spinner("Asking the LLM..."):
                llm_result = extract_skills_llm(jd_text)
            # Rename the keys so they match the spaCy categories.
            llm_groups = {
                category: llm_result[key] for key, category in LLM_KEY_TO_CATEGORY.items()
            }
            show_skill_groups(llm_groups)

            st.markdown("**Experience Requirements**")
            if llm_result["experience_requirements"]:
                for requirement in llm_result["experience_requirements"]:
                    st.write(f"- {requirement}")
            else:
                st.caption("None found")
        except LLMExtractionError as error:
            st.error(str(error))

    # ----- Comparison -----
    st.divider()
    st.subheader("Comparison")
    if llm_groups is None:
        st.info("Comparison needs LLM results. Fix the error above and try again.")
    else:
        spacy_skills = all_skills_normalized(classical_result)
        llm_skills = all_skills_normalized(llm_groups)

        # Set difference: items in the first set that are not in the second.
        only_llm = sorted(llm_skills - spacy_skills)
        only_spacy = sorted(spacy_skills - llm_skills)
        both = sorted(spacy_skills & llm_skills)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Only the LLM found** ({len(only_llm)})")
            st.write(", ".join(only_llm) or "—")
        with c2:
            st.markdown(f"**Only spaCy found** ({len(only_spacy)})")
            st.write(", ".join(only_spacy) or "—")
        with c3:
            st.markdown(f"**Both found** ({len(both)})")
            st.write(", ".join(both) or "—")
