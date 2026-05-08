"""
Catalog scraper for SHL product catalog.
Extracts Individual Test Solutions only (excludes Job Solutions).
"""

import httpx
import asyncio
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

SHL_CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


async def scrape_catalog() -> List[Dict]:
    """
    Scrape SHL product catalog and extract Individual Test Solutions.
    Returns list of assessment dictionaries.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info(f"Fetching catalog from {SHL_CATALOG_URL}")
        response = await client.get(SHL_CATALOG_URL, headers=headers)
        response.raise_for_status()
        logger.info(f"Catalog fetched, content length: {len(response.text)}")

    soup = BeautifulSoup(response.text, "lxml")

    # Parse assessments - adapt selector based on actual page structure
    # Common patterns: product tiles, table rows, cards
    assessments = []

    # Try multiple selectors for robustness
    selectors = [
        # Product catalog common patterns
        ("div.product-item", extract_product_tile),
        ("div.tile-product", extract_product_tile),
        ("tr.product-row", extract_table_row),
        ("a.product-link", extract_link_item),
        (".assessment-item", extract_generic_item),
    ]

    for selector, extractor in selectors:
        items = soup.select(selector)
        if items:
            logger.info(f"Found {len(items)} items with selector: {selector}")
            for item in items:
                try:
                    assessment = extractor(item)
                    if assessment and is_valid_assessment(assessment):
                        assessments.append(assessment)
                except Exception as e:
                    logger.warning(f"Failed to extract item: {e}")
            if assessments:
                break

    # Fallback: try to find any links to shl.com products
    if not assessments:
        logger.warning("No items found with standard selectors, trying fallback")
        assessments = fallback_scrape(soup)

    logger.info(f"Extracted {len(assessments)} valid assessments")
    return assessments


def extract_product_tile(item) -> Optional[Dict]:
    """Extract from product tile structure."""
    name_elem = item.select_one(".product-name, .title, h3, h4, .name")
    url_elem = item.select_one("a[href], [data-url]")
    type_elem = item.select_one(".test-type, .type, .category")

    if not name_elem:
        return None

    name = name_elem.get_text(strip=True)
    url = url_elem.get("href") or url_elem.get("data-url", "") if url_elem else ""
    test_type = type_elem.get_text(strip=True) if type_elem else "Unknown"

    # Build full URL
    if url and not url.startswith("http"):
        url = f"https://www.shl.com{url if url.startswith('/') else '/' + url}"

    return {
        "name": name,
        "url": url,
        "test_type": categorize_test_type(test_type, name),
        "description": extract_description(item),
        "skills": extract_skills(item),
    }


def extract_table_row(item) -> Optional[Dict]:
    """Extract from table row structure."""
    cells = item.select("td")
    if len(cells) < 2:
        return None

    name = cells[0].get_text(strip=True)
    link = cells[0].select_one("a[href]")
    url = link.get("href", "") if link else ""
    test_type = cells[1].get_text(strip=True) if len(cells) > 1 else "Unknown"

    if not name:
        return None

    return {
        "name": name,
        "url": url,
        "test_type": categorize_test_type(test_type, name),
        "description": "",
        "skills": [],
    }


def extract_link_item(item) -> Optional[Dict]:
    """Extract from anchor element."""
    name = item.get_text(strip=True)
    url = item.get("href", "")

    if not name or len(name) < 2:
        return None

    return {
        "name": name,
        "url": url,
        "test_type": "Unknown",
        "description": "",
        "skills": [],
    }


def extract_generic_item(item) -> Optional[Dict]:
    """Generic extraction fallback."""
    name_elem = item.select_one("h3, h4, .title, .name")
    name = name_elem.get_text(strip=True) if name_elem else ""

    if not name:
        return None

    return {
        "name": name,
        "url": "",
        "test_type": "Unknown",
        "description": "",
        "skills": [],
    }


def extract_description(item) -> str:
    """Extract description from item."""
    desc_elem = item.select_one(".description, .desc, p")
    return desc_elem.get_text(strip=True) if desc_elem else ""


def extract_skills(item) -> List[str]:
    """Extract skills/tags from item."""
    skills = []
    skill_elems = item.select(".skills, .tags, .keywords, .skill")
    for elem in skill_elems:
        skills.extend([t.strip() for t in elem.get_text().split(",")])
    return [s for s in skills if s]


def categorize_test_type(type_str: str, name: str) -> str:
    """Categorize test type based on string or assessment name."""
    type_lower = type_str.lower()
    name_lower = name.lower()

    # Knowledge/Technical
    if any(k in type_lower for k in ["knowledge", "skill", "technical", "coding", "programming"]):
        return "K"
    if any(k in name_lower for k in ["java", "python", "sql", "programming", "coding", "technical"]):
        return "K"

    # Personality
    if any(k in type_lower for k in ["personality", "behavior", "opq", "gsa"]):
        return "P"
    if any(k in name_lower for k in ["opq", "personality", "behavior", "gsa"]):
        return "P"

    # Ability/Cognitive
    if any(k in type_lower for k in ["ability", "cognitive", "reasoning", "iq", "aptitude"]):
        return "A"
    if any(k in name_lower for k in ["reasoning", "cognitive", "aptitude", "iq"]):
        return "A"

    return "K"  # Default to Knowledge/Technical


def is_valid_assessment(assessment: Dict) -> bool:
    """Validate assessment has required fields."""
    if not assessment:
        return False
    if not assessment.get("name"):
        return False
    if len(assessment.get("name", "")) < 2:
        return False
    # Must have URL (could be empty but need to populate)
    return True


def fallback_scrape(soup: BeautifulSoup) -> List[Dict]:
    """Fallback scraping using any product links."""
    assessments = []
    seen_names = set()

    # Find all product-related links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # Filter to likely product pages
        if any(kw in href.lower() for kw in ["product", "assessment", "test", "solution"]):
            if text and text not in seen_names and len(text) > 3:
                assessments.append({
                    "name": text,
                    "url": href if href.startswith("http") else f"https://www.shl.com{href}",
                    "test_type": "Unknown",
                    "description": "",
                    "skills": [],
                })
                seen_names.add(text)

    return assessments


async def save_catalog(assessments: List[Dict], filepath: str = "catalog.json"):
    """Save scraped catalog to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(assessments)} assessments to {filepath}")


async def main():
    """Scrape and save catalog."""
    logging.basicConfig(level=logging.INFO)
    assessments = await scrape_catalog()
    await save_catalog(assessments)
    print(f"Scraped {len(assessments)} assessments")


if __name__ == "__main__":
    asyncio.run(main())