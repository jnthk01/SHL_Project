"""Catalog package for SHL assessment data."""

from .loader import (
    load_catalog,
    CatalogManager,
    get_assessment_by_name,
    get_assessments_by_type,
    search_catalog,
    FALLBACK_CATALOG,
)

__all__ = [
    "load_catalog",
    "CatalogManager",
    "get_assessment_by_name",
    "get_assessments_by_type",
    "search_catalog",
    "FALLBACK_CATALOG",
]