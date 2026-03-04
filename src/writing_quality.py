from typing import Dict
from src.readbility import WritingQualityAnalyzer


def normalize_score(value, min_val, max_val):
    """Normalize value to 0–100 range."""
    if value is None:
        return 0.0
    value = max(min_val, min(value, max_val))
    return (value - min_val) / (max_val - min_val) * 100


def score_readability(metrics: dict) -> float:
    """Convert readability metrics into single score."""
    if not metrics:
        return 0.0

    flesch = normalize_score(metrics.get("flesch_reading_ease"), 0, 100)
    smog = 100 - normalize_score(metrics.get("smog_index"), 0, 20)
    grade = 100 - normalize_score(metrics.get("flesch_kincaid_grade"), 0, 20)

    return round((flesch + smog + grade) / 3, 2)


def score_grammar(metrics: dict) -> float:
    """Estimate grammar quality score."""
    if not metrics:
        return 0.0

    word_count = metrics.get("word_count", 0)
    avg_word_length = metrics.get("avg_word_length", 0)

    length_score = normalize_score(avg_word_length, 3, 10)
    structure_score = normalize_score(word_count, 0, 1000)

    return round((length_score + structure_score) / 2, 2)


def score_style(metrics: dict) -> float:
    """Score academic writing style."""
    if not metrics:
        return 0.0

    passive_penalty = metrics.get("passive_voice_ratio", 0) * 100
    first_person_penalty = metrics.get("first_person_ratio", 0) * 100
    informal_penalty = metrics.get("informal_language_count", 0) * 20

    score = 100 - (0.4 * passive_penalty +
                   0.4 * first_person_penalty +
                   0.2 * informal_penalty)

    return round(max(0, score), 2)


def analyze_writing_quality(sections: Dict[str, str]) -> Dict[str, float]:
    """
    Main function for AI paper review analyzer.
    Returns final writing quality scores.
    """
    analyzer = WritingQualityAnalyzer()

    readability_scores = []
    grammar_scores = []
    style_scores = []
    coherence_scores = []

    for text in sections.values():
        if not isinstance(text, str) or not text.strip():
            continue

        readability = analyzer.compute_readability(text)
        grammar = analyzer.grammar_analysis(text)

        doc = analyzer.nlp(text) if analyzer.nlp else None
        style = {
            "passive_voice_ratio": analyzer.passive_voice_ratio(doc),
            "first_person_ratio": analyzer.first_person_ratio(doc),
            "informal_language_count": analyzer.informal_language_count(text),
        }

        coherence = analyzer.coherence_score(text)

        readability_scores.append(score_readability(readability))
        grammar_scores.append(score_grammar(grammar))
        style_scores.append(score_style(style))
        coherence_scores.append(coherence * 100 if coherence else 0)

    writing_quality = {
        "readability_score": round(sum(readability_scores)/len(readability_scores), 2) if readability_scores else 0,
        "grammar_score": round(sum(grammar_scores)/len(grammar_scores), 2) if grammar_scores else 0,
        "style_score": round(sum(style_scores)/len(style_scores), 2) if style_scores else 0,
        "coherence_score": round(sum(coherence_scores)/len(coherence_scores), 2) if coherence_scores else 0
    }

    return writing_quality



