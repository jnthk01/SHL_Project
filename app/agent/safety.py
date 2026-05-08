"""
Safety and scope control - handles refusals and off-topic detection.
Ensures agent stays within SHL assessment scope.
"""

import re
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


# Unsafe/off-topic patterns
REFUSAL_PATTERNS = {
    # Legal topics
    r"\b(legal|lawyer|attorney|compliance|regulatory|lawsuit|discrimination|termination|workers compensation|employment laws|employment law)\b": {
        "topic": "legal advice",
        "message": "I'm focused on SHL assessment recommendations. For legal questions, please consult a qualified legal professional."
    },

    # Compensation/salary topics
    r"\b(salary|compensation|pay|wages|benefits|bonus|stock options|equity)\b": {
        "topic": "compensation advice",
        "message": "I specialize in SHL assessment recommendations. For compensation benchmarking, please consult HR or industry salary surveys."
    },

    # Hiring policy
    r"\b(how.*(hire|fire|promote|demote)|hiring policy|recruitment policy|termination|redundancy)\b": {
        "topic": "hiring policy",
        "message": "I can help with SHL assessment recommendations. For hiring policies, please check with your HR department."
    },

    # Non-SHL products - only if explicitly asking for recommendations
    r"\b(aws certified|microsoft certified|cisco certified|pmp certification|itil certification|comptia certification)\b": {
        "topic": "non-SHL certifications",
        "message": "I only recommend SHL assessments. For other certifications, please consult the relevant certification bodies."
    },

    # Discrimination/EEOC topics
    r"\b(discriminat|bias|fairness| EEOC|equal.*opportunity|protected.*class|quota)\b": {
        "topic": "discrimination advice",
        "message": "For questions about fair hiring practices and compliance, please consult your legal/HR team."
    },

    # General career advice (not assessment related)
    r"\b(career.*advice|resume|cv|interview.*tips|job.*search|career.*networking)\b": {
        "topic": "career advice",
        "message": "I can help you find SHL assessments for your hiring needs. For career advice, consider a career counselor."
    },
}


# Prompt injection patterns
INJECTION_PATTERNS = [
    # Instruction override attempts
    r"ignore (all )?(previous|prior) (instructions?|rules?|prompt)",
    r"(ignore|bypass|disregard) (all )?(safety|previous|instructions)",
    r"system(.*)prompt",
    r"#.*instruction",
    r"you (are now|should now|must now)",
    r"forget (everything|all)",
    r"new.*(instruction|prompt|rule)",
    r"act as (a|an) (different|new|alternative)",
    r"pretend (to be|you are)",
    r"roleplay.*as.*different",
    r"ignore previous",
    r"ignore all",
    r"\\x00",  # Null bytes
    r"\]\s*\[",  # JSON injection attempt
]


class SafetyChecker:
    """
    Checks user input for safety violations and off-topic requests.
    """

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self._refusal_patterns = {}
        for pattern, config in REFUSAL_PATTERNS.items():
            self._refusal_patterns[re.compile(pattern, re.IGNORECASE)] = config

        self._injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
        ]

    def check_safety(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains safety violations.

        Args:
            text: User input text

        Returns:
            Tuple of (is_safe, refusal_message)
            - is_safe: False if unsafe, True if safe
            - refusal_message: Message to return if unsafe
        """
        if not text:
            return True, None

        # Check for prompt injection
        for pattern in self._injection_patterns:
            if pattern.search(text):
                logger.warning(f"Prompt injection detected: {text[:50]}...")
                return False, "I can't process that request. Let's focus on SHL assessments."

        # Check for refusal topics
        for pattern, config in self._refusal_patterns.items():
            if pattern.search(text):
                logger.info(f"Off-topic detected: {config['topic']}")
                return False, config["message"]

        return True, None

    def is_off_topic(self, text: str, context: dict = None) -> bool:
        """
        Determine if message is off-topic for SHL assessments.

        Args:
            text: User message
            context: Optional context from conversation

        Returns:
            True if off-topic, False if relevant
        """
        if not text:
            return False

        text_lower = text.lower()

        # Topics that are definitely off-topic
        off_topic_keywords = [
            "weather", "sports", "news", "politics", "religion",
            "entertainment", "music", "movies", "food", "travel",
        ]

        # Check if it's purely conversational (not assessment-related)
        if any(kw in text_lower for kw in off_topic_keywords):
            # But allow if there's any assessment-related content
            assessment_related = [
                "test", "assessment", "evaluate", "candidate", "hire",
                "job", "role", "skills", "competency", "personality",
                "cognitive", "technical", "interview",
            ]
            if not any(kw in text_lower for kw in assessment_related):
                return True

        return False

    def check_grounding(self, recommendations: list, catalog: list) -> Tuple[bool, List[dict]]:
        """
        Verify all recommendations exist in catalog.
        Critical for preventing hallucinations.

        Args:
            recommendations: List of recommendation dicts
            catalog: List of catalog items

        Returns:
            Tuple of (all_valid, valid_recommendations)
        """
        if not recommendations:
            return True, []

        # Build catalog name set (lowercase for comparison)
        catalog_names = {item.get("name", "").lower() for item in catalog}
        catalog_urls = {item.get("url", "") for item in catalog}

        valid_recommendations = []
        invalid_count = 0

        for rec in recommendations:
            name = rec.get("name", "").lower()
            url = rec.get("url", "")

            # Check name exists in catalog
            if name in catalog_names:
                valid_recommendations.append(rec)
            # Also check if it's a partial match
            elif any(name in cn for cn in catalog_names):
                valid_recommendations.append(rec)
            else:
                logger.warning(f"Hallucinated assessment detected: {rec.get('name')}")
                invalid_count += 1

        if invalid_count > 0:
            logger.error(f"Found {invalid_count} hallucinated recommendations")

        all_valid = invalid_count == 0
        return all_valid, valid_recommendations


# Global safety checker instance
_safety_checker: Optional[SafetyChecker] = None


def get_safety_checker() -> SafetyChecker:
    """Get global safety checker instance."""
    global _safety_checker
    if _safety_checker is None:
        _safety_checker = SafetyChecker()
    return _safety_checker


def check_message_safety(text: str) -> Tuple[bool, Optional[str]]:
    """Convenience function for safety checking."""
    checker = get_safety_checker()
    return checker.check_safety(text)


def validate_recommendations(recommendations: list, catalog: list) -> Tuple[bool, List[dict]]:
    """Convenience function for grounding validation."""
    checker = get_safety_checker()
    return checker.check_grounding(recommendations, catalog)