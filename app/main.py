"""
SHL Assessment Recommender - Main FastAPI Application
A conversational retrieval agent for SHL assessment recommendations.
"""

import logging
import time
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List as PydanticList

# Import components
from app.models import Message, ChatRequest, ChatResponse, Recommendation
from app.catalog import CatalogManager, load_catalog
from app.agent import create_agent
from app.retrieval import initialize_vector_store, get_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
_catalog_manager: CatalogManager = None
_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global _catalog_manager, _agent

    logger.info("Starting SHL Assessment Recommender...")

    # Load catalog
    catalog = load_catalog()
    _catalog_manager = CatalogManager()
    logger.info(f"Loaded {len(catalog)} assessments from catalog")

    # Skip vector store initialization for faster startup
    # Keyword search works perfectly for this use case
    logger.info("Using keyword-based search for recommendations")

    # Create agent
    _agent = create_agent(_catalog_manager)
    logger.info("Agent initialized")

    yield

    # Cleanup
    logger.info("Shutting down...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="SHL Assessment Recommender",
    description="Conversational agent for SHL assessment recommendations",
    version="1.0.0",
    lifespan=lifespan
)


# ============== API Endpoints ==============

@app.get("/health")
async def health():
    """Health check endpoint - returns OK if service is ready."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - stateless conversation processing.

    Accepts full conversation history and returns next agent reply
    with recommendations when appropriate.
    """
    start_time = time.time()

    # Validate input
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Ensure agent is initialized
    if _agent is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Process conversation
        response = _agent.process(request.messages)

        # Log processing time
        elapsed = time.time() - start_time
        logger.info(f"Processed request in {elapsed:.2f}s, recommendations: {len(response.recommendations)}")

        return response

    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Additional Endpoints (Optional) ==============

@app.get("/catalog/count")
async def catalog_count():
    """Get total number of assessments in catalog."""
    if _catalog_manager is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return {"count": len(_catalog_manager.catalog)}


@app.get("/catalog/search")
async def catalog_search(q: str, limit: int = 10):
    """Simple keyword search in catalog."""
    if _catalog_manager is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = _catalog_manager.search(q)[:limit]
    return {"results": results}


# ============== Root ==============

@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "SHL Assessment Recommender",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat (POST)",
            "catalog_count": "/catalog/count",
            "catalog_search": "/catalog/search?q=...",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)