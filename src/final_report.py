"""
Final report generator: combines writing quality, section analysis, and novelty
into a human-readable review with per-section feedback and overall scores.
"""
from typing import Dict, List, Any


def _format_score(name: str, score: float) -> str:
    return f"{name}: {score}/100"


def generate_suggestions_for_section(section_name: str, weak_issues: List[str], novelty_score: float, writing_scores: Dict[str, float]) -> List[str]:
    suggestions = []

    # Handle empty or too short
    if any("Empty" in issue for issue in weak_issues):
        suggestions.append("Add substantive content to this section. Start with a clear topic sentence and include supporting evidence or citations.")
    if any("Too short" in issue for issue in weak_issues):
        suggestions.append("Expand this section: include more background, details, or examples to reach an adequate length.")
    if any("placeholder" in issue.lower() for issue in weak_issues):
        suggestions.append("Replace placeholder text with full content and concrete results.")
    if any("Very few sentences" in issue for issue in weak_issues):
        suggestions.append("Add more sentences and explanations to improve clarity and depth.")

    # Style/grammar related guidance (if available)
    if writing_scores:
        g = writing_scores.get("grammar_score", 0)
        s = writing_scores.get("style_score", 0)
        if g < 60:
            suggestions.append("Proofread for grammar: check sentence boundaries and punctuation; consider running a grammar tool.")
        if s < 60:
            suggestions.append("Adjust tone and voice: reduce passive voice and first-person phrasing for academic style.")

    # Novelty guidance
    if novelty_score < 40:
        suggestions.append("This section appears similar to existing literature in the corpus; emphasize your unique contributions, new experiments, or novel analysis.")
    elif novelty_score < 60:
        suggestions.append("Partially novel: clarify distinctions with related work and highlight incremental contributions.")
    else:
        suggestions.append("Section is novel compared to the corpus; ensure claims are well-supported and clearly stated.")

    # Consolidate and return
    # Remove duplicates while preserving order
    seen = set()
    out = []
    for s in suggestions:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def generate_final_report(writing_quality: Dict[str, Any], section_analysis: Dict[str, Any], novelty_map: Dict[str, float]) -> Dict[str, Any]:
    """
    Assemble final report data structure and a printable summary.

    Returns a dict containing:
      - overall_scores: combined scores
      - per_section: list of sections with metrics and suggestions
      - summary: textual summary
    """
    report = {
        "overall_scores": {},
        "per_section": [],
        "summary": "",
    }

    # Overall writing quality
    if isinstance(writing_quality, dict):
        report["overall_scores"]["readability_score"] = writing_quality.get("readability_score", 0)
        report["overall_scores"]["grammar_score"] = writing_quality.get("grammar_score", 0)
        report["overall_scores"]["style_score"] = writing_quality.get("style_score", 0)
        report["overall_scores"]["coherence_score"] = writing_quality.get("coherence_score", 0)

    # Section weak list
    weak_list = section_analysis.get("weak_sections", []) if section_analysis else []
    weak_map = {w["section"]: w for w in weak_list} if weak_list else {}

    for section_name in section_analysis.get("section_names", []):
        word_count = section_analysis.get("section_word_counts", {}).get(section_name, 0)
        issues = weak_map.get(section_name, {}).get("issues", []) if weak_map else []
        novelty = novelty_map.get(section_name, None) if novelty_map else None

        # For writing_scores per-section we don't have breakdown; use overall writing_quality as proxy
        suggestions = generate_suggestions_for_section(section_name, issues, novelty if novelty is not None else 100.0, writing_quality)

        entry = {
            "section": section_name,
            "word_count": word_count,
            "issues": issues,
            "novelty": novelty,
            "suggestions": suggestions
        }
        report["per_section"].append(entry)

    # Compute aggregate novelty if available
    if novelty_map:
        avg_novelty = round(sum(novelty_map.values()) / len(novelty_map), 2)
        report["overall_scores"]["novelty_score"] = avg_novelty

    # Simple textual summary
    summary_lines = []
    summary_lines.append("Final Review Summary:")
    if report["overall_scores"]:
        for k, v in report["overall_scores"].items():
            summary_lines.append(f" - {k.replace('_', ' ').title()}: {v}")

    # Top recommendations aggregated
    top_recs = []
    for sec in report["per_section"]:
        for s in sec["suggestions"]:
            if s not in top_recs:
                top_recs.append(s)
    if top_recs:
        summary_lines.append("Top Recommendations:")
        for r in top_recs[:10]:
            summary_lines.append(f"  * {r}")

    report["summary"] = "\n".join(summary_lines)
    return report


def print_report(report: Dict[str, Any]) -> None:
    print("\n" + "#"*60)
    print("FINAL REVIEW REPORT")
    print("#"*60 + "\n")

    # Overall scores
    if report.get("overall_scores"):
        print("Overall Scores:")
        for k, v in report["overall_scores"].items():
            print(f" - {k.replace('_',' ').title()}: {v}")
        print()

    # Per-section details
    print("Per-section Analysis:")
    for sec in report.get("per_section", []):
        print(f"\nSection: {sec['section']}")
        print(f" Word count: {sec['word_count']}")
        if sec.get("novelty") is not None:
            print(f" Novelty: {sec['novelty']}/100")
        if sec.get("issues"):
            print(" Issues:")
            for it in sec["issues"]:
                print(f"  - {it}")
        if sec.get("suggestions"):
            print(" Suggestions:")
            for s in sec["suggestions"]:
                print(f"  -> {s}")

    # Summary
    print("\n" + "#"*20)
    print(report.get("summary", ""))
    print("#"*20 + "\n")
