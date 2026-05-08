"""
Utility functions for parsing and text processing.
"""

import re
from typing import List, Dict, Optional, Tuple


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    return re.sub(r'\s+', ' ', text).strip()


def extract_numbers(text: str) -> List[int]:
    """Extract all numbers from text."""
    return [int(m) for m in re.findall(r'\d+', text)]


def extract_role_from_text(text: str) -> Optional[str]:
    """Extract job role from text."""
    text_lower = text.lower()

    # Common role patterns
    patterns = [
        r'(?:hiring|looking for|need|seeking)\s+(?:a\s+)?(\w+\s+developer)',
        r'(?:hiring|looking for|need|seeking)\s+(?:a\s+)?(\w+\s+engineer)',
        r'(?:hiring|looking for|need|seeking)\s+(?:a\s+)?(\w+\s+analyst)',
        r'(?:hiring|looking for|need|seeking)\s+(?:a\s+)?(\w+\s+manager)',
        r'(\w+)\s+developer',
        r'(\w+)\s+engineer',
        r'(\w+)\s+analyst',
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)

    return None


def extract_seniority_from_text(text: str) -> Optional[str]:
    """Extract seniority level from text."""
    text_lower = text.lower()

    senior_keywords = ["senior", "lead", "principal", "staff", "architect", "expert", "4+ years", "5+ years"]
    junior_keywords = ["junior", "entry", "graduate", "trainee", "intern", "entry-level", "1-2 years"]
    mid_keywords = ["mid", "intermediate", "3-4 years", "mid-level"]

    for kw in senior_keywords:
        if kw in text_lower:
            return "senior"
    for kw in junior_keywords:
        if kw in text_lower:
            return "junior"
    for kw in mid_keywords:
        if kw in text_lower:
            return "mid"

    return None


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    return re.split(r'[.!?]+', text)


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_url(url: str) -> str:
    """Clean and validate URL."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def format_test_type(test_type: str) -> str:
    """Format test type for display."""
    mapping = {
        "K": "Knowledge/Skills",
        "A": "Ability/Cognitive",
        "P": "Personality/Behavioral",
        "KA": "Knowledge & Ability",
        "KP": "Knowledge & Personality",
    }
    return mapping.get(test_type.upper(), test_type)


def parse_job_description(text: str) -> Dict:
    """Parse job description for key information."""
    result = {
        "skills": [],
        "seniority": None,
        "role": None,
        "stakeholder": False,
        "coding": False,
        "leadership": False,
    }

    text_lower = text.lower()

    # Skills
    common_skills = [
        "java", "python", "sql", "javascript", "typescript", "c++", "c#",
        "react", "angular", "vue", "node", "django", "flask",
        "aws", "azure", "gcp", "docker", "kubernetes", "devops",
        "machine learning", "data science", "ai", "deep learning",
        "agile", "scrum", "jira",
        "communication", "leadership", "project management",
    ]
    for skill in common_skills:
        if skill in text_lower:
            result["skills"].append(skill)

    # Seniority
    result["seniority"] = extract_seniority_from_text(text)

    # Role
    result["role"] = extract_role_from_text(text)

    # Boolean flags
    result["stakeholder"] = any(kw in text_lower for kw in ["stakeholder", "client", "customer facing", "present"])
    result["coding"] = any(kw in text_lower for kw in ["coding", "programming", "developer"])
    result["leadership"] = any(kw in text_lower for kw in ["lead", "manage", "team lead", "head of"])

    return result


def fuzzy_match(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """
    Simple fuzzy string matching.
    Returns True if strings are similar above threshold.
    """
    text1_lower = text1.lower()
    text2_lower = text2.lower()

    if text1_lower == text2_lower:
        return True

    # Check if one contains the other
    if text1_lower in text2_lower or text2_lower in text1_lower:
        return True

    # Simple word overlap
    words1 = set(text1_lower.split())
    words2 = set(text2_lower.split())

    if not words1 or not words2:
        return False

    overlap = len(words1 & words2) / len(words1 | words2)
    return overlap >= threshold


class TextCleaner:
    """Utility class for text cleaning."""

    @staticmethod
    def remove_punctuation(text: str) -> str:
        return re.sub(r'[^\w\s]', '', text)

    @staticmethod
    def remove_extra_spaces(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def lowercase(text: str) -> str:
        return text.lower()

    @staticmethod
    def clean(text: str) -> str:
        """Full cleaning pipeline."""
        text = TextCleaner.remove_punctuation(text)
        text = TextCleaner.remove_extra_spaces(text)
        return text.lower()


def extract_comparison_entities(text: str) -> List[str]:
    """Extract assessment names from comparison request."""
    text_lower = text.lower()

    # Patterns for "X vs Y", "difference between X and Y"
    patterns = [
        r'difference between\s+(.+?)\s+and\s+(.+)',
        r'compare\s+(.+?)\s+and\s+(.+)',
        r'(.+?)\s+(?:vs|versus)\s+(.+)',
    ]

    entities = []
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities.extend([match.group(1).strip(), match.group(2).strip()])

    return [e for e in entities if len(e) > 1]