"""
Module for analyzing extracted sections in research papers.
Identifies missing standard sections and detects weak sections based on content.
"""

from typing import Dict, List


# Standard sections found in academic papers
STANDARD_SECTIONS = {
    "abstract": "Abstract - Summary of the entire paper",
    "introduction": "Introduction - Background and motivation",
    "related_work": "Related Work - Literature review",
    "methodology": "Methodology/Methods - How the research was conducted",
    "results": "Results - Key findings",
    "discussion": "Discussion - Interpretation of results",
    "conclusion": "Conclusion - Final thoughts and future work",
    "references": "References - Cited sources"
}

# Minimum word counts for sections to be considered adequate
MIN_SECTION_LENGTH = {
    "abstract": 100,
    "introduction": 200,
    "related_work": 300,
    "methodology": 300,
    "results": 200,
    "discussion": 300,
    "conclusion": 150,
    "references": 50
}


def analyze_section_structure(sections: Dict[str, str]) -> Dict:
    """
    Analyze the structural completeness of extracted sections.
    
    Args:
        sections: Dictionary with section names as keys and content as values
        
    Returns:
        Dictionary with analysis results including missing sections and weak sections
    """
    analysis = {
        "total_sections_found": len(sections),
        "section_names": list(sections.keys()),
        "missing_standard_sections": [],
        "present_standard_sections": [],
        "weak_sections": [],
        "section_word_counts": {},
        "section_quality_issues": {}
    }
    
    # Count words in each section
    for section_name, content in sections.items():
        word_count = len(content.split()) if content else 0
        analysis["section_word_counts"][section_name] = word_count
        analysis["section_quality_issues"][section_name] = []
    
    # Check for standard sections
    extracted_sections_lower = {s.lower(): s for s in sections.keys()}
    
    for standard_section in STANDARD_SECTIONS.keys():
        found = False
        for extracted_section in extracted_sections_lower.keys():
            if standard_section in extracted_section.lower() or extracted_section.lower() in standard_section:
                found = True
                analysis["present_standard_sections"].append(standard_section)
                break
        
        if not found:
            analysis["missing_standard_sections"].append(standard_section)
    
    # Identify weak sections
    for section_name, content in sections.items():
        word_count = analysis["section_word_counts"][section_name]
        issues = []
        
        # Check word count
        section_key = section_name.lower()
        min_length = MIN_SECTION_LENGTH.get(section_key, 100)
        
        if word_count == 0:
            issues.append("Empty section - no content")
        elif word_count < min_length:
            issues.append(f"Too short - {word_count} words (minimum: {min_length})")
        
        # Check for placeholder text or low information density
        if content:
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            if len(lines) < 3:
                issues.append("Very few sentences - lacks detail")
            
            # Check for common placeholder patterns
            if any(placeholder in content.lower() for placeholder in 
                   ['TODO', 'FIXME', 'write here', 'to be filled', 'placeholder']):
                issues.append("Contains placeholder text")
        
        if issues:
            analysis["weak_sections"].append({
                "section": section_name,
                "word_count": word_count,
                "issues": issues
            })
    
    return analysis


def check_section_completeness(sections: Dict[str, str]) -> Dict:
    """
    Check what sections are present and what are missing.
    
    Args:
        sections: Dictionary with section names and content
        
    Returns:
        Dictionary with completeness information
    """
    completeness = {
        "present": [],
        "missing": [],
        "completion_rate": 0.0,
        "required_sections": list(STANDARD_SECTIONS.keys()),
        "recommendations": []
    }
    
    section_names_lower = {s.lower() for s in sections.keys()}
    
    # Check each standard section
    for standard in STANDARD_SECTIONS.keys():
        found = False
        for extracted in section_names_lower:
            if standard in extracted or extracted in standard:
                found = True
                completeness["present"].append(STANDARD_SECTIONS[standard])
                break
        
        if not found:
            completeness["missing"].append(STANDARD_SECTIONS[standard])
            completeness["recommendations"].append(f"Add {standard.title()} section")
    
    # Calculate completion rate
    completeness["completion_rate"] = len(completeness["present"]) / len(STANDARD_SECTIONS) * 100
    
    return completeness


def get_weak_section_details(sections: Dict[str, str]) -> List[Dict]:
    """
    Get detailed information about weak sections.
    
    Args:
        sections: Dictionary with sections
        
    Returns:
        List of weak sections with details
    """
    analysis = analyze_section_structure(sections)
    weak_section_details = []
    
    for weak in analysis["weak_sections"]:
        section_name = weak["section"]
        content = sections.get(section_name, "")
        
        details = {
            "section": section_name,
            "word_count": weak["word_count"],
            "issues": weak["issues"],
            "content_preview": content[:200] + "..." if len(content) > 200 else content,
            "recommendations": []
        }
        
        # Add specific recommendations
        for issue in weak["issues"]:
            if "Too short" in issue:
                details["recommendations"].append("Expand this section with more details and analysis")
            elif "Empty" in issue:
                details["recommendations"].append("Add content to this section")
            elif "Very few sentences" in issue:
                details["recommendations"].append("Add more substantive paragraphs")
            elif "placeholder" in issue.lower():
                details["recommendations"].append("Replace placeholder text with actual content")
        
        weak_section_details.append(details)
    
    return weak_section_details


def print_section_analysis_report(sections: Dict[str, str]) -> None:
    """
    Print comprehensive section analysis report.
    
    Args:
        sections: Dictionary with extracted sections
    """
    print("\n" + "="*60)
    print("SECTION STRUCTURE ANALYSIS")
    print("="*60)
    
    # Completeness check
    completeness = check_section_completeness(sections)
    
    print(f"\n📊 PAPER COMPLETENESS: {completeness['completion_rate']:.1f}%")
    print(f"   Standard Sections Present: {len(completeness['present'])}/{len(STANDARD_SECTIONS)}")
    
    if completeness["present"]:
        print("\n✓ PRESENT SECTIONS:")
        for section in completeness["present"]:
            print(f"  • {section}")
    
    if completeness["missing"]:
        print("\n✗ MISSING SECTIONS:")
        for section in completeness["missing"]:
            print(f"  • {section}")
    
    # Weak sections
    weak_details = get_weak_section_details(sections)
    
    if weak_details:
        print("\n⚠️  WEAK SECTIONS DETECTED:")
        for weak in weak_details:
            print(f"\n  📌 {weak['section'].upper()}")
            print(f"     Word Count: {weak['word_count']}")
            print(f"     Issues:")
            for issue in weak["issues"]:
                print(f"       - {issue}")
            print(f"     Recommendations:")
            for rec in weak["recommendations"]:
                print(f"       → {rec}")
    else:
        print("\n✓ All sections have adequate content!")
    
    # Recommendations
    if completeness["recommendations"]:
        print("\n💡 OVERALL RECOMMENDATIONS:")
        for rec in completeness["recommendations"]:
            print(f"  • {rec}")
    
    print("\n" + "="*60)
