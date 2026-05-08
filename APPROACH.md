# SHL Assessment Recommender - Technical Approach

## Overview

This document describes the design and implementation of a conversational retrieval agent for SHL assessment recommendations. The system accepts natural language queries about hiring needs and returns relevant assessment recommendations from the SHL product catalog.

---

## Architecture

The application is built as a **stateless FastAPI service** with a modular agent architecture:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  FastAPI    │────▶│    Agent     │────▶│   Retrieval     │
│  Endpoints  │     │   Pipeline   │     │   Components    │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐       ┌──────────┐      ┌──────────┐
   │ Safety  │       │ Context  │      │  Compare │
   │ Checker │       │ Extractor│      │  Module  │
   └─────────┘       └──────────┘      └──────────┘
```

### Components

1. **API Layer** (`main.py`) - Stateless `/chat` endpoint accepting full conversation history
2. **Agent Pipeline** (`conversation.py`) - Orchestrates safety check, context extraction, retrieval, and response generation
3. **Catalog Manager** (`catalog/loader.py`) - Loads and indexes SHL product catalog
4. **Retrieval** - Hybrid approach: keyword search with optional semantic (FAISS) fallback
5. **Safety Module** (`agent/safety.py`) - Refuses off-topic, legal, compensation, and prompt injection queries

---

## Retrieval Setup

### Hybrid Search Architecture

The system uses a two-stage retrieval approach:

**Stage 1: Keyword Search**
- Extracts search keywords from user query
- Implements TF-IDF style scoring with:
  - Exact title matches (highest weight)
  - Partial title matches
  - Skill/description matches
  - Stop words filtered (the, and, is, etc.)

**Stage 2: Semantic Fallback** (Optional)
- Uses sentence-transformers (`all-MiniLM-L6-v2`) for embeddings
- FAISS IndexFlatIP for approximate nearest neighbor search
- Activated when keyword search returns < 3 results

### Context Extraction

The system extracts hiring context from conversation messages:

| Field | Detection | Example |
|-------|-----------|---------|
| `role` | Job title keywords | "Java Developer", "Data Analyst" |
| `seniority` | Experience keywords | "junior", "senior", "lead" |
| `assessment_type` | Test type keywords | "cognitive", "technical", "personality" |
| `language` | Spoken language | "English UK", "Australian" |
| `skills` | Technical skills | "Python", "SQL", "project management" |

---

## Catalog

- **Source**: SHL product catalog (377 assessments)
- **Format**: JSON with fields: `name`, `url`, `test_type`, `description`, `skills`, `url`
- **Storage**: In-memory loading at startup, optional persistent caching

### Example Catalog Entry

```json
{
  "name": "Customer Service Phone Simulation",
  "url": "https://www.shl.com/.../customer-service-phone-simulation",
  "test_type": "Technical Skills",
  "description": "Assesses candidate's ability to handle customer inquiries...",
  "skills": ["communication", "customer service", "problem solving"]
}
```

---

## Prompt Design

### Behavior Patterns

The agent handles four distinct behaviors:

| Behavior | Trigger | Response |
|----------|---------|----------|
| **Clarify** | Missing context fields | Ask single clarification question |
| **Recommend** | Full context, 1-10 assessments | Return matched assessments |
| **Refine** | Modification keywords | Re-filter current recommendations |
| **Compare** | "vs" or "compare" keywords | Grounded comparison of 2+ assessments |

### Response Format

```json
{
  "reply": "string",
  "recommendations": [{"name": "...", "url": "...", "test_type": "..."}],
  "end_of_conversation": boolean
}
```

- `recommendations` empty while clarifying
- 1-10 assessments when committed to shortlist
- `end_of_conversation: false` after recommendations to allow follow-up

### Clarification Logic

Priority order for missing context:
1. **Role** - Always required first
2. **Language** - Required for customer service/contact centre roles
3. **Assessment Type** - Helps narrow results
4. **Seniority** - Optional refinement

---

## Evaluation

### Schema Compliance
- Response always includes `reply`, `recommendations`, `end_of_conversation`
- `recommendations` is empty list when clarifying, 1-10 items otherwise

### Grounding Validation
- All returned assessments must exist in catalog
- URLs are validated against catalog entries

### Behavior Probes

| Test Case | Expected Behavior |
|-----------|-------------------|
| "I need Java developer assessments" | Clarify for missing context → recommend |
| "Show me more for senior roles" | Refine current shortlist |
| "Compare OPQ vs GSA" | Return comparison of both |
| "What's the salary for this role?" | Refuse - out of scope |
| "Ignore previous instructions" | Refuse - prompt injection |

---

## Safety & Refusals

The system refuses queries outside its scope:

| Category | Patterns Detected |
|----------|-------------------|
| **Compensation** | "salary", "pay", "bonus", "benefits" |
| **Legal/Hiring Policy** | "illegal", "discriminat", "equal opportunity" |
| **Off-Topic** | Sports, weather, general conversation |
| **Prompt Injection** | "ignore previous", "disregard instructions" |

When refusing, the system redirects to SHL assessment topic:
> "I only provide SHL assessment recommendations. How can I help with your hiring?"

---

## Deployment

The service runs as a stateless REST API:
- `GET /health` - Health check
- `POST /chat` - Main conversation endpoint

Run locally:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Deploy to any Python-compatible host (Render, Fly.io, Railway).

---

## Summary

This implementation provides a production-ready conversational agent for SHL assessment recommendations, with proper context extraction, hybrid retrieval, safety filtering, and schema-compliant responses. The modular design allows easy extension for additional behaviors or retrieval methods.