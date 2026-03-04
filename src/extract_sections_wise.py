import re


class SectionExtractor:
    """Extract sections from academic papers with support for Roman numerals, digits, and variant spellings."""

    def __init__(self):
        """Initialize with standard academic section patterns."""
        # Support both traditional names and common aliases
        self.section_patterns = {
            "abstract": r"abstract",
            "introduction": r"introduction",
            "related_work": r"(?:related\s+work|literature\s+review)",
            "methodology": r"(?:methodology|methods|Model Architecture|Proposed Method|METHOD PROPOSED|Proposed Methodology|materials\s+and\s+methods)",
            "results": r"(?i)\b[IVXLCDM]+\.?\s+RESULTS?\b",
            "discussion": r"discussion",
            "conclusion": r"(?:conclusion|conclusions|summary)",
            #"references": r"(?mi)^\s*[IVXLCDM]*\.?\s*REFERENCES\s*$",
        }
        # Prefix to match optional section numbers
        # Matches: "1.", "I.", "II)", "&III.", etc., with optional punctuation
        self.prefix = r"(?:[^\w\s]{0,2}(?:[IVXLCDM]{1,4}|\d{1,2})[\.\)]*\s*)?"

    def _normalize_text(self, text: str) -> str:
        """Normalize unicode spaces and collapse repeated whitespace."""
        # Replace common unicode spaces with regular spaces
        text = text.replace('\u00A0', ' ').replace('\xa0', ' ')
        text = text.replace('\u200B', '').replace('\u2009', ' ').replace('\u202F', ' ')
        # Collapse multiple spaces/tabs
        text = re.sub(r'[ \t]{2,}', ' ', text)
        return text

    def extract_sections(self, text: str) -> dict:
        """Extract section text blocks from document."""
        text = self._normalize_text(text)
        positions = {}

        # Build regex patterns with optional prefixes
        for section_key, pattern_base in self.section_patterns.items():
            full_pattern = self.prefix + r"\b" + pattern_base + r"\b"
            try:
                match = re.search(full_pattern, text, flags=re.I)
                if match:
                    positions[section_key] = match.start()
            except re.error:
                continue

        if not positions:
            return {}

        sorted_sections = sorted(positions.items(), key=lambda x: x[1])
        extracted = {}

        for i, (section, start) in enumerate(sorted_sections):
            end = sorted_sections[i + 1][1] if i + 1 < len(sorted_sections) else len(text)
            extracted[section] = text[start:end].strip()

        return extracted


# Backwards-compatible wrapper
def extract_sections(text: str) -> dict:
    """Extract sections from text using default SectionExtractor."""
    extractor = SectionExtractor()
    return extractor.extract_sections(text)


def debug_extraction(text: str) -> dict:
    """Print detection info for debugging."""
    extractor = SectionExtractor()
    text = extractor._normalize_text(text)
    positions = {}

    print("\n=== SECTION DETECTION DEBUG ===")
    for section_key, pattern_base in extractor.section_patterns.items():
        full_pattern = extractor.prefix + r"\b" + pattern_base + r"\b"
        try:
            match = re.search(full_pattern, text, flags=re.I)
            if match:
                positions[section_key] = match.start()
                matchtext = text[match.start():match.start() + 50]
                print(f"✓ {section_key:15} @ pos {match.start():6}  |  {repr(matchtext)}")
            else:
                print(f"✗ {section_key:15} NOT FOUND")
        except re.error as e:
            print(f"✗ {section_key:15} ERROR: {e}")

    print("=== END DEBUG ===\n")
    return positions
