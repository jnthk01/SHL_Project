"""
Comparison feature - handles comparing two or more assessments.
Extracts real data from catalog, no hallucinations.
"""

import logging
import re
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger(__name__)


class ComparisonEngine:
    """
    Generates grounded comparisons between SHL assessments.
    Uses only catalog data - never hallucinates.
    """

    def detect_comparison_request(self, text: str) -> Optional[Tuple[List[str], str]]:
        """
        Detect if user is asking for comparison.

        Args:
            text: User message

        Returns:
            Tuple of (assessment_names, comparison_type) or None
        """
        text_lower = text.lower()

        # Comparison patterns
        patterns = [
            # "difference between X and Y"
            r"difference between\s+(.+?)\s+(?:and|vs|versus)\s+(.+)",
            # "compare X and Y"
            r"compare\s+(.+?)\s+(?:and|vs|versus)\s+(.+)",
            # "X vs Y" or "X versus Y"
            r"(.+?)\s+(?:vs|versus)\s+(.+)",
            # "what is the difference between X and Y"
            r"what (?:is the |)'?s? difference between\s+(.+?)\s+and\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                names = [match.group(1).strip(), match.group(2).strip()]
                # Clean up names - remove trailing punctuation
                cleaned = []
                for n in names:
                    n = re.sub(r'[^\w\s-].*$', '', n)  # Remove trailing punctuation
                    n = n.strip()
                    if n and len(n) > 1:
                        cleaned.append(n)
                if len(cleaned) >= 2:
                    return cleaned, pattern

        return None

    def compare_assessments(
        self,
        names: List[str],
        catalog: List[Dict],
        max_length: int = 500
    ) -> str:
        """
        Generate comparison text for named assessments.

        Args:
            names: List of assessment names to compare (1-3)
            catalog: Full catalog for lookup
            max_length: Maximum response length

        Returns:
            Grounded comparison text
        """
        if not names or len(names) < 2:
            return "I need at least two assessments to compare."

        assessments = []
        for name in names:
            match = self._find_assessment(name, catalog)
            if match:
                assessments.append(match)
            else:
                # Try to find similar names
                similar = self._find_similar(name, catalog)
                if similar:
                    assessments.append(similar)
                else:
                    logger.warning(f"Could not find assessment: {name}")

        if len(assessments) < 2:
            found_names = [a.get("name", "?") for a in assessments]
            return f"I couldn't find all the assessments you mentioned. Found: {', '.join(found_names)}"

        # Build comparison
        comparison = self._build_comparison(assessments)

        # Truncate if needed
        if len(comparison) > max_length:
            comparison = comparison[:max_length-3] + "..."

        return comparison

    def _find_assessment(self, name: str, catalog: List[Dict]) -> Optional[Dict]:
        """Find assessment by exact or partial name match."""
        name_lower = name.lower().strip()

        # Exact match
        for item in catalog:
            if item.get("name", "").lower() == name_lower:
                return item

        # For short acronyms like "GSA", "OPQ", try to match in name abbreviations
        # Also match if the short name appears in the item name
        for item in catalog:
            item_name = item.get("name", "").lower()
            # Check if name appears in item name (e.g., "gsa" in "global skills assessment")
            if name_lower in item_name:
                return item
            # Also check if item name starts with the search term (e.g., "opq" starts with "opq")
            if item_name.startswith(name_lower):
                return item

        return None

    def _find_similar(self, name: str, catalog: List[Dict], max_results: int = 3) -> Optional[Dict]:
        """Find similar assessments when exact match fails."""
        name_lower = name.lower().strip()

        # Extract key terms (letters and numbers only)
        key_terms = re.findall(r'[a-z0-9]+', name_lower)

        if not key_terms:
            return None

        # Find items with matching key terms
        matches = []
        for item in catalog:
            item_name = item.get("name", "").lower()
            score = sum(1 for term in key_terms if term in item_name)
            if score > 0:
                matches.append((score, item))

        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            return matches[0][1]

        return None

    def _build_comparison(self, assessments: List[Dict]) -> str:
        """Build structured comparison text from assessment data."""
        lines = []

        for i, a in enumerate(assessments):
            name = a.get("name", "Unknown")
            test_type = a.get("test_type", "Unknown")
            desc = a.get("description", "")
            skills = a.get("skills", [])

            lines.append(f"\n**{name}**")
            lines.append(f"- Type: {self._format_test_type(test_type)}")
            if desc:
                lines.append(f"- Description: {desc}")
            if skills:
                lines.append(f"- Skills: {', '.join(skills[:5])}")

        # Add comparison header
        result = f"Here's a comparison of {len(assessments)} assessments:\n"
        result += "\n".join(lines)

        # Add summary
        result += "\n\n**Summary:**\n"
        result += self._generate_summary(assessments)

        return result

    def _format_test_type(self, test_type: str) -> str:
        """Format test type for display."""
        type_map = {
            "K": "Knowledge/Skills",
            "A": "Ability/Cognitive",
            "P": "Personality/Behavioral",
        }
        return type_map.get(test_type, test_type)

    def _generate_summary(self, assessments: List[Dict]) -> str:
        """Generate brief summary comparing the assessments."""
        if not assessments:
            return ""

        # Group by test type
        by_type = {}
        for a in assessments:
            tt = a.get("test_type", "U")
            if tt not in by_type:
                by_type[tt] = []
            by_type[tt].append(a.get("name", "?"))

        # Build summary
        summary_parts = []
        for tt, names in by_type.items():
            type_label = self._format_test_type(tt)
            summary_parts.append(f"- {type_label}: {', '.join(names)}")

        return "\n".join(summary_parts)


# Global comparison engine
_comparison_engine: Optional[ComparisonEngine] = None


def get_comparison_engine() -> ComparisonEngine:
    """Get global comparison engine."""
    global _comparison_engine
    if _comparison_engine is None:
        _comparison_engine = ComparisonEngine()
    return _comparison_engine


def detect_and_compare(
    text: str,
    catalog: List[Dict]
) -> Optional[str]:
    """
    Convenience function to detect comparison and return result.

    Args:
        text: User message
        catalog: Full catalog

    Returns:
        Comparison text or None if not a comparison request
    """
    engine = get_comparison_engine()
    result = engine.detect_comparison_request(text)

    if result:
        names, pattern = result
        return engine.compare_assessments(names, catalog)

    return None