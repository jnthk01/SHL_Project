"""
Refinement logic - handles updating recommendations based on user feedback.
Uses conversation history to incrementally update query context.
"""

import logging
import re
from typing import Optional, List, Dict, Tuple
# Note: Using Pydantic .model_dump() instead of dataclasses asdict

from ..models import QueryContext

logger = logging.getLogger(__name__)


class RefinementDetector:
    """
    Detects and handles refinement requests from user.
    Examples: "add personality tests", "make it more junior", "remove cognitive"
    """

    # Refinement action patterns
    ACTION_PATTERNS = {
        # Add something
        r"(?:also\s+)?(?:add|include|also\s+want|need|with)\s+(.+?)(?:\s|$)": "add",
        # Remove something
        r"(?:remove|exclude|without|don't\s+want|no\s+)(.+?)(?:\s|$)": "remove",
        # Change/make more/less
        r"(?:make\s+it\s+)?(more|less)\s+(.+)": "change",
        # Focus on
        r"focus\s+on\s+(.+)": "focus",
        # Actually/like to change
        r"(?:actually|I'd\s+like\s+to|i\s+want\s+to)\s+(.+?)(?:\s+instead|$)": "replace",
    }

    # Assessment type keywords mapping
    TYPE_KEYWORDS = {
        "personality": ["personality", "behavior", "opq", "gsa", "behavioral"],
        "cognitive": ["cognitive", "reasoning", "iq", "aptitude", "ability", "logical"],
        "technical": ["technical", "skill", "knowledge", "coding", "programming"],
        "skills": ["skills", "skill-based"],
    }

    def detect_refinement(self, text: str) -> Optional[Dict]:
        """
        Detect if message is a refinement request.

        Args:
            text: User message

        Returns:
            Dict with action, target, and value, or None
        """
        text_lower = text.lower()

        for pattern, action in self.ACTION_PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                target = match.group(1).strip() if match.lastindex >= 1 else ""

                # Extract refinement details
                refinement = {
                    "action": action,
                    "target": self._classify_target(target),
                    "original": text,
                }

                logger.info(f"Detected refinement: {refinement}")
                return refinement

        return None

    def _classify_target(self, text: str) -> Dict:
        """Classify what user wants to add/remove/change."""
        text_lower = text.lower()

        # Check for assessment types
        for atype, keywords in self.TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return {"type": "assessment_type", "value": atype}

        # Check for seniority
        if any(kw in text_lower for kw in ["junior", "entry", "graduate"]):
            return {"type": "seniority", "value": "junior"}
        if any(kw in text_lower for kw in ["senior", "lead", "principal"]):
            return {"type": "seniority", "value": "senior"}
        if any(kw in text_lower for kw in ["mid", "mid-level", "intermediate"]):
            return {"type": "seniority", "value": "mid"}

        # Check for specific skills
        skill_keywords = [
            "java", "python", "sql", "javascript", "coding",
            "communication", "leadership", "management",
            "analysis", "data", "cloud"
        ]
        for skill in skill_keywords:
            if skill in text_lower:
                return {"type": "skill", "value": skill}

        # Check for role
        role_keywords = ["developer", "engineer", "analyst", "manager", "designer"]
        for role in role_keywords:
            if role in text_lower:
                return {"type": "role", "value": role}

        return {"type": "unknown", "value": text}

    def apply_refinement(
        self,
        current_context: QueryContext,
        refinement: Dict
    ) -> QueryContext:
        """
        Apply refinement to existing query context.

        Args:
            current_context: Current query context
            refinement: Refinement dict from detect_refinement

        Returns:
            Updated QueryContext
        """
        action = refinement.get("action", "")
        target = refinement.get("target", {})
        target_type = target.get("type", "")
        target_value = target.get("value", "")

        # Create new context (immutable update)
        context_dict = current_context.model_dump()

        if action == "add":
            if target_type == "assessment_type":
                if target_value not in context_dict["assessment_types"]:
                    context_dict["assessment_types"].append(target_value)
            elif target_type == "skill":
                if target_value not in context_dict["skills"]:
                    context_dict["skills"].append(target_value)
            elif target_type == "seniority":
                context_dict["seniority"] = target_value

        elif action == "remove":
            if target_type == "assessment_type":
                context_dict["assessment_types"] = [
                    at for at in context_dict["assessment_types"]
                    if at != target_value
                ]
            elif target_type == "skill":
                context_dict["skills"] = [
                    s for s in context_dict["skills"]
                    if s != target_value
                ]

        elif action == "change" or action == "replace":
            if target_type == "seniority":
                context_dict["seniority"] = target_value
            elif target_type == "assessment_type":
                context_dict["assessment_types"] = [target_value]

        elif action == "focus":
            # Reset and set new focus
            if target_type == "skill":
                context_dict["skills"] = [target_value]
            elif target_type == "assessment_type":
                context_dict["assessment_types"] = [target_value]
            elif target_type == "role":
                context_dict["roles"] = [target_value]

        logger.info(f"Applied refinement, new context: {context_dict}")
        return QueryContext(**context_dict)

    def is_refinement_message(self, messages: List[Dict]) -> bool:
        """
        Check if conversation is in refinement state.

        Args:
            messages: List of message dicts

        Returns:
            True if last assistant message contained recommendations
        """
        if len(messages) < 2:
            return False

        # Look at last assistant message
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # If it contains recommendations, user might be refining
                return "recommend" in content.lower() or "here are" in content.lower()

        return False


class RefinementHandler:
    """
    High-level handler for refinement workflow.
    """

    def __init__(self):
        self._detector = RefinementDetector()

    def process_refinement(
        self,
        user_message: str,
        current_context: QueryContext,
        prior_recommendations: List[Dict]
    ) -> Tuple[QueryContext, List[Dict], str]:
        """
        Process a refinement request.

        Args:
            user_message: Latest user message
            current_context: Current query context
            prior_recommendations: Previously returned recommendations

        Returns:
            Tuple of (new_context, new_recommendations, response_text)
        """
        # Detect refinement
        refinement = self._detector.detect_refinement(user_message)

        if not refinement:
            # Not a refinement, treat as new query
            return current_context, [], None

        # Apply refinement to context
        new_context = self._detector.apply_refinement(current_context, refinement)

        # Build response text
        response = self._build_refinement_response(refinement, prior_recommendations)

        # Return empty recommendations - they'll be regenerated via retrieval
        # based on the updated context
        return new_context, [], response

    def _build_refinement_response(
        self,
        refinement: Dict,
        prior_recs: List[Dict]
    ) -> str:
        """Build response acknowledging the refinement."""
        action = refinement.get("action", "")
        target = refinement.get("target", {})
        value = target.get("value", "")
        original = refinement.get("original", "")

        if action == "add":
            return f"Adding {value} to your criteria. Let me find updated recommendations."
        elif action == "remove":
            return f"Removing {value} from your criteria. Let me update the recommendations."
        elif action == "change" or action == "replace":
            return f"Updating to {value}. Let me find new recommendations."
        elif action == "focus":
            return f"Focusing on {value}. Let me find updated recommendations."

        return "Updating your criteria."


# Global refinement handler
_refinement_handler: Optional[RefinementHandler] = None


def get_refinement_handler() -> RefinementHandler:
    """Get global refinement handler."""
    global _refinement_handler
    if _refinement_handler is None:
        _refinement_handler = RefinementHandler()
    return _refinement_handler