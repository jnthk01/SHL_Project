"""
Main conversational agent - orchestrates all components.
Implements the complete agent flow: safety -> intent -> context -> retrieve -> respond.
"""

import logging
from typing import List, Optional, Tuple, Dict
# Note: Removed dataclasses import - using Pydantic .model_dump() instead

from ..models import Message, QueryContext, ChatResponse, Recommendation
from ..catalog import CatalogManager
from ..retrieval import (
    get_vector_store,
    initialize_vector_store,
    get_reranker,
    compute_query_embedding,
)
from .safety import get_safety_checker, validate_recommendations
from .compare import get_comparison_engine, detect_and_compare
from .refine import get_refinement_handler, RefinementDetector
from .prompts import get_prompt_generator

logger = logging.getLogger(__name__)


class ConversationalAgent:
    """
    Main conversational agent for SHL assessment recommendations.
    Stateless - processes full conversation history each request.
    """

    # Maximum clarification questions before forcing recommendation
    MAX_CLARIFICATION_TURNS = 3

    def __init__(self, catalog_manager: CatalogManager):
        self.catalog = catalog_manager
        self._safety = get_safety_checker()
        self._comparison = get_comparison_engine()
        self._refinement = get_refinement_handler()
        self._refinement_detector = RefinementDetector()
        self._prompts = get_prompt_generator()
        self._retriever = get_vector_store()
        self._reranker = get_reranker()

    def process(self, messages: List[Message]) -> ChatResponse:
        """
        Process conversation and generate response.

        Args:
            messages: Full conversation history

        Returns:
            ChatResponse with reply, recommendations, and end_of_conversation
        """
        if not messages:
            return ChatResponse(
                reply="Hello! I help find SHL assessments. What role are you hiring for?",
                recommendations=[],
                end_of_conversation=False
            )

        # Get last user message
        last_user_msg = self._get_last_user_message(messages)
        if not last_user_msg:
            return ChatResponse(
                reply="Hello! How can I help you with SHL assessments?",
                recommendations=[],
                end_of_conversation=False
            )

        # Step 1: Safety check
        is_safe, refusal_msg = self._safety.check_safety(last_user_msg.content)
        if not is_safe:
            return ChatResponse(
                reply=refusal_msg,
                recommendations=[],
                end_of_conversation=False
            )

        # Step 2: Build conversation context
        conversation_text = self._build_conversation_text(messages)
        previous_context = self._extract_context_from_history(messages)

        # Step 3: Detect comparison request
        comparison_result = detect_and_compare(
            last_user_msg.content,
            self.catalog.catalog
        )
        if comparison_result:
            return ChatResponse(
                reply=comparison_result,
                recommendations=[],
                end_of_conversation=False
            )

        # Step 4: Detect refinement request
        is_refining = self._refinement_detector.is_refinement_message([
            m.model_dump() for m in messages
        ])

        if is_refining:
            refinement_result = self._refinement.process_refinement(
                last_user_msg.content,
                previous_context,
                []
            )
            new_context = refinement_result[0]

            # Re-run retrieval with new context
            recommendations = self._retrieve_with_context(new_context)

            # Validate grounding
            valid, recommendations = validate_recommendations(
                recommendations,
                self.catalog.catalog
            )

            if recommendations:
                reply = self._prompts.generate_refinement_response(
                    {"target": {"value": last_user_msg.content}},
                    len(recommendations)
                )
                # Add recommendation names to response
                names = [r["name"] for r in recommendations]
                reply += "\n\n" + "\n".join([f"- {n}" for n in names])

                return ChatResponse(
                    reply=reply,
                    recommendations=self._convert_recommendations(recommendations),
                    end_of_conversation=True
                )

        # Step 5: Extract query context from full conversation
        query_context = self._extract_query_context(messages)

        # Step 6: Determine if clarification needed
        missing = self._check_missing_context(query_context)

        if missing:
            # Too many clarification attempts?
            clarification_count = self._count_clarification_attempts(messages)
            if clarification_count >= self.MAX_CLARIFICATION_TURNS:
                # Force recommendations with whatever we have
                recommendations = self._retrieve_with_context(query_context)
                if recommendations:
                    return self._build_recommendation_response(
                        recommendations,
                        query_context,
                        forced=True
                    )
                else:
                    return ChatResponse(
                        reply="I couldn't find matching assessments with the information provided. Could you provide more details?",
                        recommendations=[],
                        end_of_conversation=True
                    )

            # Ask clarification
            clarification = self._prompts.generate_clarification(missing)
            return ChatResponse(
                reply=clarification,
                recommendations=[],
                end_of_conversation=False
            )

        # Step 7: Retrieve and recommend
        recommendations = self._retrieve_with_context(query_context)

        if not recommendations:
            return ChatResponse(
                reply="I couldn't find matching assessments. Could you try different criteria?",
                recommendations=[],
                end_of_conversation=True
            )

        # Validate grounding - critical for no hallucinations
        valid, recommendations = validate_recommendations(
            recommendations,
            self.catalog.catalog
        )

        if not valid:
            logger.error("Grounding validation failed - filtering out invalid")

        # If all recommendations were filtered out, report failure
        if not recommendations:
            return ChatResponse(
                reply="I couldn't find valid assessments in the catalog matching your criteria. Please try different keywords.",
                recommendations=[],
                end_of_conversation=True
            )

        return self._build_recommendation_response(
            recommendations,
            query_context,
            forced=False
        )

    def _get_last_user_message(self, messages: List[Message]) -> Optional[Message]:
        """Get last user message from conversation."""
        for msg in reversed(messages):
            if msg.role == "user":
                return msg
        return None

    def _build_conversation_text(self, messages: List[Message]) -> str:
        """Build combined text from conversation."""
        return " ".join([m.content for m in messages if m.content])

    def _extract_context_from_history(self, messages: List[Message]) -> QueryContext:
        """Extract accumulated context from conversation history."""
        context = QueryContext()

        for msg in messages:
            if msg.role == "user":
                extracted = self._extract_single_message_context(msg.content)
                # Merge into context
                context.roles.extend(extracted.roles)
                context.skills.extend(extracted.skills)
                if extracted.seniority and not context.seniority:
                    context.seniority = extracted.seniority
                context.assessment_types.extend(extracted.assessment_types)

        # Deduplicate
        context.roles = list(set(context.roles))
        context.skills = list(set(context.skills))
        context.assessment_types = list(set(context.assessment_types))

        return context

    def _extract_query_context(self, messages: List[Message]) -> QueryContext:
        """
        Extract full query context from conversation.
        Parses job descriptions, role info, and preferences.
        """
        context = QueryContext()

        # Process all user messages
        for msg in messages:
            if msg.role == "user":
                extracted = self._extract_single_message_context(msg.content)
                context.roles.extend(extracted.roles)
                context.skills.extend(extracted.skills)
                if extracted.seniority:
                    context.seniority = extracted.seniority
                context.assessment_types.extend(extracted.assessment_types)

                # Check for job description
                if "jd" in msg.content.lower() or "job description" in msg.content.lower():
                    jd_skills = self._extract_from_job_description(msg.content)
                    context.skills.extend(jd_skills)
                    context.job_description = msg.content

        # Check assistant messages for user confirmations
        for msg in messages:
            if msg.role == "assistant":
                # If user confirmed something in next turn, update context
                pass

        # Deduplicate
        context.roles = list(set(context.roles))
        context.skills = list(set(context.skills))
        context.assessment_types = list(set(context.assessment_types))

        return context

    def _extract_single_message_context(self, text: str) -> QueryContext:
        """Extract context from a single message."""
        context = QueryContext()
        text_lower = text.lower()

        # Role detection
        role_patterns = [
            r"(?:hiring|recruiting|looking for|need).*?(\w+\s+developer)",
            r"(\w+\s+developer)",
            r"(\w+\s+engineer)",
            r"(\w+\s+analyst)",
            r"(\w+\s+manager)",
            r"(\w+\s+designer)",
            r"(\w+\s+specialist)",
        ]
        import re
        for pattern in role_patterns:
            match = re.search(pattern, text_lower)
            if match:
                context.roles.append(match.group(1))

        # Programming language detection as skills (use word boundaries)
        # Note: avoid single letters that might be substrings
        programming_langs = [
            "python", "java", "javascript", "typescript", "c++", "c#",
            "ruby", "go", "golang", "rust", "php", "scala", "kotlin", "swift",
            "sql", "perl", "shell", "bash"
        ]
        for lang in programming_langs:
            # Use word boundary check for single letters, substring for longer
            if len(lang) <= 2:
                # For short langs, require word boundary
                import re
                if re.search(r'\b' + lang + r'\b', text_lower):
                    context.skills.append(lang)
            else:
                # For longer langs, check substring
                if lang in text_lower:
                    context.skills.append(lang)

        # Detect spoken languages for customer service/contact centre
        spoken_languages = [
            "english", "american", "british", "australian", "indian",
            "spanish", "french", "german", "mandarin", "cantonese", "japanese",
            "korean", "portuguese", "italian", "dutch", "arabic", "hindi"
        ]
        for lang in spoken_languages:
            if lang in text_lower:
                context.skills.append(f"language:{lang}")

        # Also detect networking and systems terms
        tech_terms = [
            "networking", "network", "security", "cybersecurity", "cloud",
            "devops", "systems", "infrastructure", "embedded", "unix",
            "database", "data", "analytics", "ai", "machine learning",
            "linux", "windows", "macos", "administration", "admin",
            # Customer service / contact centre terms
            "customer service", "contact centre", "contact center", "call centre",
            "customer support", "support agent", "retail", "service agent",
            "inbound", "outbound", "phone", "voice", "spoken", "language",
            "bpo", "kpo", "shared services",
        ]
        for term in tech_terms:
            if term in text_lower and term not in context.skills:
                context.skills.append(term)

        # Also detect "assessment" queries and treat them as skill requests
        if "assessment" in text_lower or "test" in text_lower:
            # Check if there's a specific technology mentioned
            pass  # Already covered by programming langs

        # Seniority detection
        if any(w in text_lower for w in ["senior", "lead", "principal", "staff", "architect"]):
            context.seniority = "senior"
        elif any(w in text_lower for w in ["junior", "entry", "graduate", "trainee"]):
            context.seniority = "junior"
        elif any(w in text_lower for w in ["mid", "intermediate", "3 years", "4 years", "5 years"]):
            context.seniority = "mid"

        # Assessment type detection
        if any(w in text_lower for w in ["personality", "behavior", "opq", "gsa", "behavioral"]):
            context.assessment_types.append("personality")
        if any(w in text_lower for w in ["cognitive", "reasoning", "iq", "aptitude", "ability"]):
            context.assessment_types.append("cognitive")
        if any(w in text_lower for w in ["technical", "skill", "coding", "programming", "knowledge"]):
            context.assessment_types.append("technical")

        # Stakeholder detection
        if any(w in text_lower for w in ["stakeholder", "client", "customer facing", "presentation"]):
            context.stakeholder_interaction = True

        # Leadership detection
        if any(w in text_lower for w in ["lead", "manage", "team lead", "head of", "director"]):
            context.leadership = True

        # Coding detection
        if any(w in text_lower for w in ["coding", "programming", "code", "developer"]):
            context.coding_required = True

        return context

    def _extract_from_job_description(self, text: str) -> List[str]:
        """Extract skills from job description text."""
        skills = []

        # Common technical skills to look for
        tech_skills = [
            "java", "python", "sql", "javascript", "typescript", "c++", "c#",
            "go", "rust", "ruby", "php", "scala", "kotlin",
            "aws", "azure", "gcp", "cloud",
            "react", "angular", "vue", "node",
            "docker", "kubernetes", "devops",
            "machine learning", "data science", "ai",
            "sql", "nosql", "mongodb", "postgresql",
            "agile", "scrum", "jira",
        ]

        text_lower = text.lower()
        for skill in tech_skills:
            if skill in text_lower:
                skills.append(skill)

        return skills

    def _check_missing_context(self, context: QueryContext) -> List[str]:
        """Check what context is missing for recommendations."""
        missing = []

        # Need at least role, skills, OR seniority to recommend
        if not context.roles and not context.skills and not context.seniority:
            missing.append("role")
        elif not context.roles and not context.skills:
            pass

        # For customer service / contact centre roles, ask about language
        all_text = ' '.join(context.roles + context.skills).lower()
        customer_service_keywords = ['customer service', 'contact centre', 'contact center', 'call centre', 'support']
        is_customer_service = any(kw in all_text for kw in customer_service_keywords)

        # If it's customer service and we don't know the language, ask
        # (language detection would be in assessment_types or special field)
        if is_customer_service and not any('language' in str(v).lower() for v in [context.assessment_types, context.skills]):
            # Check if any language-related skill was detected
            languages = ['english', 'spanish', 'french', 'german', 'mandarin', 'hindi', 'arabic', 'portuguese']
            has_language = any(lang in all_text for lang in languages)
            if not has_language:
                missing.append("language")

        return missing

    def _count_clarification_attempts(self, messages: List[Message]) -> int:
        """Count how many clarification questions have been asked."""
        count = 0
        for msg in messages:
            if msg.role == "assistant":
                if "?" in msg.content and not any(
                    kw in msg.content.lower() for kw in ["recommend", "here are"]
                ):
                    count += 1
        return count

    def _retrieve_with_context(self, context: QueryContext) -> List[Dict]:
        """
        Retrieve assessments using query context.
        Uses hybrid retrieval: semantic + keyword + reranking.
        Includes fallback for when exact matches are not found.
        """
        # Build query string from context
        query_parts = []
        if context.roles:
            query_parts.extend(context.roles)
        if context.skills:
            query_parts.extend(context.skills)
        if context.assessment_types:
            query_parts.extend(context.assessment_types)
        if context.seniority:
            query_parts.append(context.seniority)

        query = " ".join(query_parts) if query_parts else "assessment"

        # First attempt: exact search
        keyword_results = self.catalog.search(query)[:20]

        # If no results or very few results, try fallback search
        if len(keyword_results) < 3:
            # Build fallback query with broader terms
            fallback_parts = []

            # Map specific skills to broader categories
            skill_to_broad = {
                'rust': 'programming software',
                'go': 'programming software',
                'golang': 'programming software',
                'scala': 'programming software',
                'kotlin': 'programming software',
                'aws': 'cloud computing',
                'azure': 'cloud computing',
                'gcp': 'cloud computing',
                'react': 'web frontend',
                'angular': 'web frontend',
                'vue': 'web frontend',
                'docker': 'devops',
                'kubernetes': 'devops',
                'networking': 'network infrastructure',
                'security': 'cyber',
                'ai': 'machine learning data',
                'ml': 'machine learning data',
            }

            # Add broader terms
            for skill in context.skills:
                if skill in skill_to_broad:
                    fallback_parts.append(skill_to_broad[skill])

            # Add role-based fallback
            if context.roles:
                for role in context.roles:
                    # Extract first word if it's a language (e.g., "rust engineer" -> "rust")
                    role_words = role.split()
                    if role_words and len(role_words[0]) > 2:
                        fallback_parts.append(role_words[0])

            # Add general category if still nothing
            if not fallback_parts:
                fallback_parts = ['software', 'engineering', 'programming', 'technical']

            fallback_query = " ".join(fallback_parts[:5])  # Limit to avoid too broad
            fallback_results = self.catalog.search(fallback_query)[:20]

            # Use fallback if it gives more results
            if len(fallback_results) > len(keyword_results):
                keyword_results = fallback_results

        # Return results
        results = keyword_results[:10]
        return results if isinstance(results, list) else list(results)

    def _build_recommendation_response(
        self,
        recommendations: List[Dict],
        context: QueryContext,
        forced: bool
    ) -> ChatResponse:
        """Build final recommendation response."""
        # Convert to proper format
        recs = self._convert_recommendations(recommendations)

        # Generate response text
        reply = f"Here are {len(recs)} assessments that match your criteria:\n\n"
        for r in recs:
            reply += f"- {r.name} ({r.test_type})\n"

        # Don't end conversation - user might want to confirm, ask questions, or refine
        return ChatResponse(
            reply=reply,
            recommendations=recs,
            end_of_conversation=False
        )

    def _convert_recommendations(self, assessments: List[Dict]) -> List[Recommendation]:
        """Convert assessment dicts to Recommendation models."""
        recs = []
        for a in assessments:
            recs.append(Recommendation(
                name=a.get("name", "Unknown"),
                url=a.get("url", ""),
                test_type=a.get("test_type", "K")
            ))
        return recs


def create_agent(catalog_manager: CatalogManager) -> ConversationalAgent:
    """Factory function to create agent."""
    return ConversationalAgent(catalog_manager)