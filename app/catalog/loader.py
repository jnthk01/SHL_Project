"""
Catalog loader - loads and manages SHL assessment catalog.
Provides fallback data with common SHL assessments if scraping fails.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Default catalog path - look in project root
DEFAULT_CATALOG_PATH = Path(__file__).parent.parent.parent / "catalog.json"


# Common SHL assessments (fallback data)
# Based on publicly known SHL product catalog
FALLBACK_CATALOG: List[Dict] = [
    # Technical/Programming Assessments
    {"name": "Java 8 (New)", "url": "https://www.shl.com/products/java-8-new/", "test_type": "K", "skills": ["Java", "Programming"], "description": "Java 8 programming assessment"},
    {"name": "Python 3.5 (New)", "url": "https://www.shl.com/products/python-35-new/", "test_type": "K", "skills": ["Python", "Programming"], "description": "Python 3.5 programming assessment"},
    {"name": "C# (.NET)", "url": "https://www.shl.com/products/c-sharp-dotnet/", "test_type": "K", "skills": ["C#", ".NET", "Programming"], "description": "C# .NET programming assessment"},
    {"name": "SQL (Advanced)", "url": "https://www.shl.com/products/sql-advanced/", "test_type": "K", "skills": ["SQL", "Database"], "description": "Advanced SQL assessment"},
    {"name": "JavaScript (ES6)", "url": "https://www.shl.com/products/javascript-es6/", "test_type": "K", "skills": ["JavaScript", "ES6", "Programming"], "description": "JavaScript ES6 assessment"},
    {"name": "Data Analysis with Python", "url": "https://www.shl.com/products/data-analysis-python/", "test_type": "K", "skills": ["Python", "Data Analysis", "Pandas"], "description": "Python data analysis assessment"},
    {"name": "Cloud Computing (AWS)", "url": "https://www.shl.com/products/cloud-computing-aws/", "test_type": "K", "skills": ["AWS", "Cloud"], "description": "AWS cloud computing assessment"},

    # Cognitive/Ability Assessments
    {"name": "Verify Numerical Reasoning", "url": "https://www.shl.com/products/verify-numerical-reasoning/", "test_type": "A", "skills": ["Numerical Reasoning", "Quantitative"], "description": "Numerical reasoning ability test"},
    {"name": "Verify Logical Reasoning", "url": "https://www.shl.com/products/verify-logical-reasoning/", "test_type": "A", "skills": ["Logical Reasoning", "Abstract Thinking"], "description": "Logical reasoning ability test"},
    {"name": "Verify Verbal Reasoning", "url": "https://www.shl.com/products/verify-verbal-reasoning/", "test_type": "A", "skills": ["Verbal Reasoning", "Comprehension"], "description": "Verbal reasoning ability test"},
    {"name": "Verify Spatial Reasoning", "url": "https://www.shl.com/products/verify-spatial-reasoning/", "test_type": "A", "skills": ["Spatial Reasoning", "Visual"], "description": "Spatial reasoning ability test"},
    {"name": "General Ability Test (GAT)", "url": "https://www.shl.com/products/general-ability-test/", "test_type": "A", "skills": ["General Ability", "Cognitive"], "description": "General cognitive ability assessment"},
    {"name": "Advanced Cognitive Battery", "url": "https://www.shl.com/products/advanced-cognitive-battery/", "test_type": "A", "skills": ["Cognitive", "Problem Solving"], "description": "Advanced cognitive assessment"},

    # Personality/Behavioral Assessments
    {"name": "OPQ32r", "url": "https://www.shl.com/products/opq32r/", "test_type": "P", "skills": ["Personality", "Behavioral"], "description": "Occupational Personality Questionnaire - 32 dimensions"},
    {"name": "OPQ32i", "url": "https://www.shl.com/products/opq32i/", "test_type": "P", "skills": ["Personality", "Behavioral"], "description": "OPQ32 Internet version"},
    {"name": "GSA (Global Skills Assessment)", "url": "https://www.shl.com/products/global-skills-assessment/", "test_type": "P", "skills": ["Skills", "Competencies"], "description": "Global skills and competencies assessment"},
    {"name": "MQ (Motivation Questionnaire)", "url": "https://www.shl.com/products/motivation-questionnaire/", "test_type": "P", "skills": ["Motivation", "Drive"], "description": "Motivation and engagement assessment"},
    {"name": "Integrity Questionnaire", "url": "https://www.shl.com/products/integrity-questionnaire/", "test_type": "P", "skills": ["Integrity", "Ethics"], "description": "Integrity and reliability assessment"},
    {"name": "Customer Service Personality", "url": "https://www.shl.com/products/customer-service-personality/", "test_type": "P", "skills": ["Customer Service", "Personality"], "description": "Customer service personality assessment"},

    # Skills Assessments
    {"name": "Business Analysis Skills", "url": "https://www.shl.com/products/business-analysis-skills/", "test_type": "K", "skills": ["Business Analysis", "Analytics"], "description": "Business analysis skills assessment"},
    {"name": "Project Management Skills", "url": "https://www.shl.com/products/project-management-skills/", "test_type": "K", "skills": ["Project Management", "Agile"], "description": "Project management skills assessment"},
    {"name": "Data Science Skills", "url": "https://www.shl.com/products/data-science-skills/", "test_type": "K", "skills": ["Data Science", "Machine Learning"], "description": "Data science skills assessment"},
    {"name": "Cybersecurity Skills", "url": "https://www.shl.com/products/cybersecurity-skills/", "test_type": "K", "skills": ["Cybersecurity", "Security"], "description": "Cybersecurity skills assessment"},
    {"name": "DevOps Skills", "url": "https://www.shl.com/products/devops-skills/", "test_type": "K", "skills": ["DevOps", "CI/CD"], "description": "DevOps skills assessment"},
    {"name": "Leadership Skills", "url": "https://www.shl.com/products/leadership-skills/", "test_type": "K", "skills": ["Leadership", "Management"], "description": "Leadership skills assessment"},
    {"name": "Communication Skills", "url": "https://www.shl.com/products/communication-skills/", "test_type": "K", "skills": ["Communication", "Presentation"], "description": "Communication skills assessment"},
    {"name": "Sales Skills", "url": "https://www.shl.com/products/sales-skills/", "test_type": "K", "skills": ["Sales", "Revenue"], "description": "Sales skills assessment"},
    {"name": "Financial Analysis Skills", "url": "https://www.shl.com/products/financial-analysis-skills/", "test_type": "K", "skills": ["Finance", "Analysis"], "description": "Financial analysis skills assessment"},
    {"name": "HR Skills", "url": "https://www.shl.com/products/hr-skills/", "test_type": "K", "skills": ["Human Resources", "HR"], "description": "HR skills assessment"},

    # Job-Specific Assessments
    {"name": "Java Developer Assessment", "url": "https://www.shl.com/products/java-developer/", "test_type": "K", "skills": ["Java", "Backend", "Programming"], "description": "Comprehensive Java developer assessment"},
    {"name": "Python Developer Assessment", "url": "https://www.shl.com/products/python-developer/", "test_type": "K", "skills": ["Python", "Backend", "Programming"], "description": "Comprehensive Python developer assessment"},
    {"name": "Data Analyst Assessment", "url": "https://www.shl.com/products/data-analyst/", "test_type": "K", "skills": ["Data Analysis", "SQL", "Visualization"], "description": "Comprehensive data analyst assessment"},
    {"name": "Software Engineer Assessment", "url": "https://www.shl.com/products/software-engineer/", "test_type": "K", "skills": ["Software Engineering", "Programming"], "description": "Comprehensive software engineer assessment"},
    {"name": "Product Manager Assessment", "url": "https://www.shl.com/products/product-manager/", "test_type": "K", "skills": ["Product Management", "Strategy"], "description": "Comprehensive product manager assessment"},
    {"name": "QA Engineer Assessment", "url": "https://www.shl.com/products/qa-engineer/", "test_type": "K", "skills": ["QA", "Testing"], "description": "Comprehensive QA engineer assessment"},
    {"name": "Business Analyst Assessment", "url": "https://www.shl.com/products/business-analyst/", "test_type": "K", "skills": ["Business Analysis", "Requirements"], "description": "Comprehensive business analyst assessment"},
    {"name": "System Administrator Assessment", "url": "https://www.shl.com/products/system-administrator/", "test_type": "K", "skills": ["System Admin", "Infrastructure"], "description": "System administrator assessment"},
    {"name": "Network Engineer Assessment", "url": "https://www.shl.com/products/network-engineer/", "test_type": "K", "skills": ["Networking", "Infrastructure"], "description": "Network engineer assessment"},
    {"name": "Full Stack Developer Assessment", "url": "https://www.shl.com/products/full-stack-developer/", "test_type": "K", "skills": ["Full Stack", "Frontend", "Backend"], "description": "Full stack developer assessment"},
]


def transform_shl_catalog(raw_catalog: List[Dict]) -> List[Dict]:
    """
    Transform real SHL catalog format to internal format.
    Real format: entity_id, name, link, job_levels, keys, description
    Internal format: name, url, test_type, skills, description
    """
    transformed = []

    for item in raw_catalog:
        name = item.get("name", "")
        url = item.get("link", "")

        if not name:
            continue

        # Determine test_type from keys
        keys = item.get("keys", [])
        test_type = "K"  # Default to Knowledge/Skills

        if keys:
            keys_str = " ".join(keys).lower()
            if "personality" in keys_str or "behavior" in keys_str:
                test_type = "P"
            elif "ability" in keys_str or "aptitude" in keys_str or "cognitive" in keys_str:
                test_type = "A"

        # Extract skills from description and keys
        skills = list(keys) if keys else []

        # Get job levels
        job_levels = item.get("job_levels", [])

        # Build transformed item
        transformed.append({
            "name": name,
            "url": url,
            "test_type": test_type,
            "skills": skills,
            "description": item.get("description", ""),
            "job_levels": job_levels,
            "duration": item.get("duration", ""),
            "adaptive": item.get("adaptive", "no"),
            "remote": item.get("remote", "yes"),
        })

    return transformed


def load_catalog(path: Optional[str] = None) -> List[Dict]:
    """
    Load catalog from JSON file, falling back to default data if file not found.

    Args:
        path: Optional path to catalog JSON file

    Returns:
        List of assessment dictionaries
    """
    catalog_path = Path(path) if path else DEFAULT_CATALOG_PATH

    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Try to fix any JSON issues
                # The file appears to be an array directly
                if content.strip().startswith("["):
                    raw_catalog = json.loads(content)
                else:
                    # Try to find array in the content
                    import re
                    match = re.search(r'\[.*\]', content, re.DOTALL)
                    if match:
                        raw_catalog = json.loads(match.group())
                    else:
                        raise ValueError("No JSON array found")

            # Transform to internal format
            catalog = transform_shl_catalog(raw_catalog)
            logger.info(f"Loaded and transformed {len(catalog)} assessments from {catalog_path}")
            return catalog
        except Exception as e:
            logger.warning(f"Failed to load catalog from {catalog_path}: {e}")

    logger.info(f"Using fallback catalog with {len(FALLBACK_CATALOG)} assessments")
    return FALLBACK_CATALOG.copy()


def get_assessment_by_name(name: str, catalog: List[Dict]) -> Optional[Dict]:
    """Find assessment by exact or partial name match."""
    name_lower = name.lower()

    # Exact match
    for item in catalog:
        if item.get("name", "").lower() == name_lower:
            return item

    # Partial match
    for item in catalog:
        if name_lower in item.get("name", "").lower():
            return item

    return None


def get_assessments_by_type(test_type: str, catalog: List[Dict]) -> List[Dict]:
    """Get all assessments of a specific type (K, P, A)."""
    return [item for item in catalog if item.get("test_type") == test_type]


# Common stop words to ignore
STOP_WORDS = {
    'i', 'm', 'am', 'hiring', 'looking', 'for', 'need', 'want', 'use', 'should',
    'what', 'which', 'how', 'can', 'could', 'would', 'would', 'will', 'do', 'does',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'to', 'from', 'in', 'on', 'at', 'by', 'with', 'about', 'into', 'through',
    'high', 'performance', 'infrastructure', 'help', 'please', 'thanks', 'thank',
    'engineer', 'engineering', 'position', 'role', 'job', 'candidate'
}

# High-value technical terms that should give extra weight
TECH_TERMS = {
    'programming', 'coding', 'software', 'developer', 'engineer', 'technical',
    'linux', 'unix', 'windows', 'macos', 'android', 'ios',
    'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'rust', 'scala', 'kotlin', 'php',
    'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'oracle',
    'aws', 'azure', 'gcp', 'cloud', 'docker', 'kubernetes', 'devops',
    'networking', 'network', 'security', 'cyber',
    'data', 'analytics', 'science', 'machine', 'learning', 'ai', 'ml',
    'web', 'frontend', 'backend', 'fullstack', 'full-stack',
    'agile', 'scrum', 'jira',
    'senior', 'junior', 'lead', 'principal', 'staff',
    'cognitive', 'ability', 'reasoning', 'aptitude',
    'personality', 'behavior', 'opq', 'gsa',
    'live', 'coding', 'interview',
    'smart', 'verify', 'test', 'assessment',
}


def search_catalog(query: str, catalog: List[Dict], max_results: int = 20) -> List[Dict]:
    """
    Simple keyword search in catalog.
    Used as fallback when embeddings not available.
    Uses word-level matching with relevance ranking and technical term boosting.
    """
    query_words = set(query.lower().split()) - STOP_WORDS

    # Separate tech terms from regular words
    tech_matches = query_words & TECH_TERMS
    other_matches = query_words - TECH_TERMS

    scored_results = []

    for item in catalog:
        # Build searchable text from multiple sources
        name_lower = item.get("name", "").lower()
        desc_lower = item.get("description", "").lower()
        keys_lower = " ".join(item.get("keys", [])).lower()
        skills_lower = " ".join(item.get("skills", [])).lower()

        searchable_text = f"{name_lower} {desc_lower} {keys_lower} {skills_lower}"

        score = 0

        # Check tech terms first (high weight)
        for term in tech_matches:
            if term in searchable_text:
                score += 5
                # Extra bonus if in name
                if term in name_lower:
                    score += 3

        # Check other matches (lower weight)
        for qw in other_matches:
            if len(qw) < 2:
                continue
            if qw in searchable_text:
                score += 1
                if qw in name_lower:
                    score += 1

        # Seniority bonus
        if 'senior' in query_words and 'senior' in name_lower:
            score += 2

        if score > 0:
            scored_results.append((item, score))

    # Sort by score descending
    scored_results.sort(key=lambda x: x[1], reverse=True)

    # Return just the items
    return [item for item, _ in scored_results[:max_results]]


class CatalogManager:
    """Manages catalog loading and access."""

    def __init__(self, catalog_path: Optional[str] = None):
        self._catalog = load_catalog(catalog_path)
        self._index = self._build_index()

    def _build_index(self) -> Dict[str, List[int]]:
        """Build simple inverted index for keyword search."""
        index = {}
        for i, item in enumerate(self._catalog):
            words = " ".join([
                item.get("name", ""),
                item.get("description", ""),
                " ".join(item.get("skills", [])),
            ]).lower().split()

            for word in words:
                if len(word) > 2:
                    if word not in index:
                        index[word] = []
                    index[word].append(i)
        return index

    @property
    def catalog(self) -> List[Dict]:
        return self._catalog

    def __len__(self) -> int:
        return len(self._catalog)

    def __getitem__(self, idx: int) -> Dict:
        return self._catalog[idx]

    def get_by_name(self, name: str) -> Optional[Dict]:
        return get_assessment_by_name(name, self._catalog)

    def get_by_type(self, test_type: str) -> List[Dict]:
        return get_assessments_by_type(test_type, self._catalog)

    def search(self, query: str) -> List[Dict]:
        return search_catalog(query, self._catalog)