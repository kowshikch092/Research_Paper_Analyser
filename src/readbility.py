import numpy as np
import textstat
import spacy


class WritingQualityAnalyzer:
    """Comprehensive writing quality analyzer for academic papers."""

    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = None

    def compute_readability(self, text: str) -> dict:
        if len(text.split()) < 50:
            return {
                "flesch_reading_ease": None,#How easy is this paper to read?
                "smog_index": None,#How many complex technical words are used?
                "flesch_kincaid_grade": None,#What education level is needed to understand this?
            }

        return {
            "flesch_reading_ease": round(textstat.flesch_reading_ease(text), 2),
            "smog_index": round(textstat.smog_index(text), 2),
            "flesch_kincaid_grade": round(textstat.flesch_kincaid_grade(text), 2)
        }

    def grammar_analysis(self, text: str) -> dict:
        words = text.split()
        return {
            "sentence_count": text.count('.') + text.count('!') + text.count('?'),
            "word_count": len(words),
            "avg_word_length": np.mean([len(w) for w in words]) if words else 0
        }

    def passive_voice_ratio(self, doc) -> float:
        if not doc:
            return 0.0
        passive_count = sum(1 for token in doc if token.dep_ == "nsubjpass")
        total_verbs = sum(1 for token in doc if token.pos_ == "VERB")
        return round(passive_count / total_verbs if total_verbs else 0, 2)

    def first_person_ratio(self, doc) -> float:
        if not doc:
            return 0.0
        first_person = sum(1 for token in doc if token.text.lower() in ["i", "we", "me", "us"])
        total_pronouns = sum(1 for token in doc if token.pos_ == "PRON")
        return round(first_person / total_pronouns if total_pronouns else 0, 2)

    def informal_language_count(self, text: str) -> int:
        informal_words = ["gonna", "wanna", "kinda", "sorta", "ain't", "gotta"]
        return sum(1 for word in informal_words if word in text.lower())

    def coherence_score(self, text: str) -> float:
        if not self.nlp:
            return 0.0

        doc = self.nlp(text)
        sentences = list(doc.sents)
        if len(sentences) < 2:
            return 1.0

        similarities = [
            sentences[i].similarity(sentences[i + 1])
            for i in range(len(sentences) - 1)
        ]

        return round(float(np.mean(similarities)), 2)
