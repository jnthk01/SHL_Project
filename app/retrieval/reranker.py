"""
Reranking logic for retrieval results.
Applies filters based on QueryContext to improve relevance.
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RerankConfig:
    """Configuration for reranking behavior."""
    # Weights for score components
    semantic_weight: float = 0.6
    keyword_weight: float = 0.3
    type_bonus: float = 0.1

    # Minimum score threshold
    min_score: float = 0.0

    # Max results to return
    max_results: int = 10


class Reranker:
    """
    Reranks retrieval results based on query context.
    Combines semantic similarity with keyword matching and type preferences.
    """

    def __init__(self, config: Optional[RerankConfig] = None):
        self.config = config or RerankConfig()

    def rerank(
        self,
        semantic_results: List[Tuple[dict, float]],
        keyword_results: List[Tuple[dict, float]],
        query_context: dict
    ) -> List[Tuple[dict, float]]:
        """
        Rerank and combine semantic and keyword results.

        Args:
            semantic_results: List of (assessment, semantic_score) from vector search
            keyword_results: List of (assessment, keyword_score) from text search
            query_context: Query context with roles, skills, seniority, etc.

        Returns:
            Sorted list of (assessment, combined_score) with match_reasons
        """
        # Build score mapping
        score_map = {}

        # Add semantic scores
        for assessment, score in semantic_results:
            key = assessment.get("name", "")
            if key not in score_map:
                score_map[key] = {"assessment": assessment, "semantic": 0, "keyword": 0}
            score_map[key]["semantic"] = max(score_map[key]["semantic"], score)

        # Add keyword scores
        for assessment, score in keyword_results:
            key = assessment.get("name", "")
            if key not in score_map:
                score_map[key] = {"assessment": assessment, "semantic": 0, "keyword": 0}
            score_map[key]["keyword"] = max(score_map[key]["keyword"], score)

        # Calculate combined scores
        results = []
        for key, scores in score_map.items():
            assessment = scores["assessment"]

            # Weighted combination
            combined = (
                self.config.semantic_weight * scores["semantic"] +
                self.config.keyword_weight * scores["keyword"]
            )

            # Apply type bonus based on query context
            type_bonus = self._get_type_bonus(assessment, query_context)
            combined += type_bonus

            # Apply skill matching bonus
            skill_bonus = self._get_skill_bonus(assessment, query_context)
            combined += skill_bonus

            # Filter by minimum score
            if combined >= self.config.min_score:
                results.append((assessment, combined))

        # Sort by combined score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Limit to max results
        return results[:self.config.max_results]

    def _get_type_bonus(self, assessment: dict, context: dict) -> float:
        """Apply bonus for matching test type preference."""
        test_type = assessment.get("test_type", "")
        assessment_types = context.get("assessment_types", [])

        if not assessment_types:
            return 0

        # Map assessment types to test types
        type_mapping = {
            "cognitive": "A",
            "ability": "A",
            "personality": "P",
            "behavioral": "P",
            "technical": "K",
            "skills": "K",
            "knowledge": "K",
        }

        for at in assessment_types:
            mapped = type_mapping.get(at.lower(), "")
            if mapped == test_type:
                return self.config.type_bonus

        return 0

    def _get_skill_bonus(self, assessment: dict, context: dict) -> float:
        """Apply bonus for matching specific skills."""
        bonus = 0

        # Check skills match
        assessment_skills = [s.lower() for s in assessment.get("skills", [])]
        context_skills = [s.lower() for s in context.get("skills", [])]

        for skill in context_skills:
            for a_skill in assessment_skills:
                if skill in a_skill or a_skill in skill:
                    bonus += 0.02  # Small bonus per skill match
                    break

        return min(bonus, 0.1)  # Cap at 0.1

    def rerank_simple(
        self,
        results: List[Tuple[dict, float]],
        query_context: dict,
        max_results: int = 10
    ) -> List[Tuple[dict, float]]:
        """
        Simple reranking when only one result list available.
        Applies contextual boosting without combination.
        """
        reranked = []

        for assessment, base_score in results:
            boosted_score = base_score

            # Apply type bonus
            boosted_score += self._get_type_bonus(assessment, query_context)

            # Apply skill bonus
            boosted_score += self._get_skill_bonus(assessment, query_context)

            # Seniority matching bonus
            boosted_score += self._match_seniority(assessment, query_context)

            reranked.append((assessment, boosted_score))

        # Re-sort by boosted score
        reranked.sort(key=lambda x: x[1], reverse=True)

        return reranked[:max_results]

    def _match_seniority(self, assessment: dict, context: dict) -> float:
        """Apply bonus for seniority level matching."""
        seniority = context.get("seniority", "")
        if not seniority:
            return 0

        name = assessment.get("name", "").lower()
        desc = assessment.get("description", "").lower()

        # Senior-level keywords
        senior_keywords = ["senior", "lead", "principal", "staff", "architect", "expert", "manager"]
        # Junior-level keywords
        junior_keywords = ["junior", "entry", "associate", "trainee", "intern", "graduate"]

        if seniority == "senior":
            if any(kw in name or kw in desc for kw in senior_keywords):
                return 0.05
            # Small penalty for junior keywords
            if any(kw in name or kw in desc for kw in junior_keywords):
                return -0.02

        elif seniority == "junior":
            if any(kw in name or kw in desc for kw in junior_keywords):
                return 0.05
            if any(kw in name or kw in desc for kw in senior_keywords):
                return -0.02

        elif seniority == "mid":
            # Mid-level - neutral, slight bonus for "developer" or "engineer"
            if "developer" in name or "engineer" in name:
                return 0.02

        return 0


def apply_filters(
    results: List[Tuple[dict, float]],
    query_context: dict,
    strict: bool = False
) -> List[Tuple[dict, float]]:
    """
    Apply hard filters to results based on query context.
    Removes results that don't match critical constraints.

    Args:
        results: List of (assessment, score) tuples
        query_context: Query context with constraints
        strict: If True, removes non-matching; if False, penalizes heavily

    Returns:
        Filtered results with adjusted scores
    """
    filtered = []

    for assessment, score in results:
        keep = True
        adjusted_score = score

        # Filter by test type if specified
        if query_context.get("assessment_types"):
            test_type = assessment.get("test_type", "")
            type_mapping = {
                "cognitive": "A", "ability": "A",
                "personality": "P", "behavioral": "P",
                "technical": "K", "skills": "K", "knowledge": "K",
            }

            matching_types = [
                type_mapping.get(at.lower(), "")
                for at in query_context["assessment_types"]
            ]

            if matching_types and test_type not in matching_types:
                if strict:
                    keep = False
                else:
                    adjusted_score -= 0.3  # Penalty instead of removal

        if keep:
            filtered.append((assessment, adjusted_score))

    return filtered


# Global reranker instance
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker