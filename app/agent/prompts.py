"""
Prompt templates for the conversational agent.
Kept concise and deterministic for fast responses.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PromptConfig:
    """Configuration for prompt generation."""
    max_context_length: int = 500
    max_response_length: int = 300
    include_examples: bool = False


class PromptGenerator:
    """
    Generates prompts for the agent.
    Uses template-based approach for determinism.
    """

    # Clarification question templates
    CLARIFICATION_TEMPLATES = {
        "role": [
            "What role are you hiring for? (e.g., Java Developer, Data Analyst, Project Manager)",
            "Which position are you trying to fill?",
            "What type of role are you recruiting for?",
        ],
        "seniority": [
            "What seniority level are you looking for? (junior, mid-level, senior, lead)",
            "What's the experience level for this role?",
            "What level of expertise do you need?",
        ],
        "assessment_type": [
            "What type of assessments are you interested in? (technical skills, cognitive ability, personality)",
            "Would you like cognitive tests, personality questionnaires, technical skills tests, or a combination?",
            "What assessment categories are relevant for your hiring needs?",
        ],
        "language": [
            "What spoken language does the role require? (e.g., English US, UK, Australian, Spanish)",
            "Which language variant do you need the assessment in?",
            "What language will the candidates be assessed in?",
        ],
        "stakeholder": [
            "Will this role involve frequent stakeholder interaction?",
            "Does the position require working with clients or internal teams?",
        ],
        "coding": [
            "Is coding or technical programming part of the role?",
            "Do you need technical/编程 assessments?",
        ],
    }

    # Response templates
    RESPONSE_TEMPLATES = {
        "initial_greeting": [
            "Hello! I help you find SHL assessments for your hiring needs. What role are you hiring for?",
            "Hi! I can help you find the right SHL assessments. What position are you looking to fill?",
        ],
        "recommendation_intro": [
            "Here are {count} assessments that match your criteria:",
            "Based on your requirements, I recommend these {count} assessments:",
            "I've found {count} assessments that fit your hiring needs:",
        ],
        "recommendation_outro": [
            "You can find more details at the provided URLs.",
            "Click the links for complete assessment information.",
            "Visit the SHL catalog pages for full details.",
        ],
        "refinement_acknowledgment": [
            "Understood. Let me update the recommendations.",
            "Got it. I'll refine the results.",
            "I'll update based on your feedback.",
        ],
        "no_results": [
            "I couldn't find matching assessments. Could you try different keywords?",
            "No assessments matched your criteria. Please try alternative search terms.",
            "I couldn't find suitable SHL assessments for your requirements. Try different criteria.",
        ],
        "off_topic": [
            "I'm focused on SHL assessment recommendations. How can I help with your hiring needs?",
            "I specialize in SHL tests. What roles are you hiring for?",
        ],
        "refusal": [
            "I only provide SHL assessment recommendations. How can I help with your hiring?",
            "I'm not able to help with that. I focus on SHL assessment selection.",
        ],
    }

    def __init__(self, config: Optional[PromptConfig] = None):
        self.config = config or PromptConfig()

    def generate_clarification(self, missing_fields: List[str]) -> str:
        """
        Generate clarification question for missing fields.

        Args:
            missing_fields: List of missing context fields

        Returns:
            Single clarification question
        """
        questions = []

        for field in missing_fields:
            if field in self.CLARIFICATION_TEMPLATES:
                # Get first template for field
                template = self.CLARIFICATION_TEMPLATES[field][0]
                questions.append(template)

        if not questions:
            return "Could you provide more details about your hiring needs?"

        # Limit to most critical questions (avoid 8-turn cap issues)
        return questions[0]

    def generate_recommendation_response(
        self,
        recommendations: List[Dict],
        context: Dict
    ) -> str:
        """
        Generate response with recommendations.

        Args:
            recommendations: List of assessment recommendations
            context: Query context

        Returns:
            Response text
        """
        count = len(recommendations)

        # Intro
        intro_key = "recommendation_intro"
        intro_template = self.RESPONSE_TEMPLATES[intro_key][0]
        intro = intro_template.format(count=count)

        # Build list of recommendations
        rec_list = []
        for rec in recommendations[:10]:  # Max 10
            name = rec.get("name", "Unknown")
            rec_list.append(f"- {name}")

        # Outro
        outro_key = "recommendation_outro"
        outro_template = self.RESPONSE_TEMPLATES[outro_key][0]

        response = f"{intro}\n\n" + "\n".join(rec_list) + f"\n\n{outro_template}"

        return response

    def generate_comparison_response(
        self,
        comparison_text: str
    ) -> str:
        """Generate response with comparison."""
        return comparison_text

    def generate_refinement_response(
        self,
        refinement: Dict,
        new_count: int
    ) -> str:
        """Generate response acknowledging refinement."""
        target = refinement.get("target", {})
        value = target.get("value", "")

        return f"Updated recommendations based on your feedback about {value}. Here are {new_count} matching assessments:"

    def generate_end_conversation(self) -> str:
        """Generate closing when task is complete."""
        return "Feel free to ask if you need more recommendations or have questions about specific assessments."

    def get_random_template(self, key: str) -> str:
        """Get random template for a key (for variety)."""
        import random
        templates = self.RESPONSE_TEMPLATES.get(key, [""])
        return random.choice(templates)


# Global prompt generator
_prompt_generator: Optional[PromptGenerator] = None


def get_prompt_generator() -> PromptGenerator:
    """Get global prompt generator."""
    global _prompt_generator
    if _prompt_generator is None:
        _prompt_generator = PromptGenerator()
    return _prompt_generator


def generate_clarification(missing_fields: List[str]) -> str:
    """Convenience function."""
    return get_prompt_generator().generate_clarification(missing_fields)


def generate_recommendation_response(
    recommendations: List[Dict],
    context: Dict
) -> str:
    """Convenience function."""
    return get_prompt_generator().generate_recommendation_response(recommendations, context)