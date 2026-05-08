"""Agent package for conversational AI."""

from .conversation import ConversationalAgent, create_agent
from .safety import get_safety_checker, check_message_safety, validate_recommendations
from .compare import get_comparison_engine, detect_and_compare
from .refine import get_refinement_handler, RefinementDetector
from .prompts import get_prompt_generator, PromptGenerator, PromptConfig

__all__ = [
    "ConversationalAgent",
    "create_agent",
    "get_safety_checker",
    "check_message_safety",
    "validate_recommendations",
    "get_comparison_engine",
    "detect_and_compare",
    "get_refinement_handler",
    "RefinementDetector",
    "get_prompt_generator",
    "PromptGenerator",
    "PromptConfig",
]