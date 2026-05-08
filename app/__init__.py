"""SHL Assessment Recommender package."""

from .models import Message, ChatRequest, ChatResponse, Recommendation
from .catalog import CatalogManager, load_catalog

__version__ = "1.0.0"