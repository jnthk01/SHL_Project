# SHL Assessment Recommender

A conversational retrieval agent for SHL assessment recommendations. This FastAPI service helps recruiters find suitable SHL assessments based on natural language queries about hiring needs.

## Features

- **Conversational Interface** - Natural language queries for assessment recommendations
- **Four Behavior Modes** - Clarify, Recommend, Refine, Compare
- **Hybrid Retrieval** - Keyword search with semantic fallback
- **Safety Filtering** - Refuses off-topic, legal, compensation, and prompt injection queries
- **Schema-Compliant** - Returns exact JSON format: `{reply, recommendations, end_of_conversation}`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/chat` | POST | Main conversation endpoint |

## Request Format

```json
{
  "messages": [
    {"role": "user", "content": "I need assessments for a Java Developer role"}
  ]
}
```

## Response Format

```json
{
  "reply": "Here are 5 assessments that match your criteria:",
  "recommendations": [
    {"name": "...", "url": "...", "test_type": "..."}
  ],
  "end_of_conversation": false
}
```

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Deploy to Render

1. Push this code to GitHub
2. Connect your GitHub repo to [Render.com](https://render.com)
3. Deploy automatically via `render.yaml`

## Example Conversations

**Clarify**: User asks about "contact centre" → System asks for spoken language preference

**Recommend**: User provides role "Java Developer", seniority "senior" → Returns matching assessments

**Refine**: User says "show me more for mid-level" → Filters previous results

**Compare**: User asks "compare OPQ vs GSA" → Returns grounded comparison

## Tech Stack

- FastAPI
- Pydantic
- FAISS (optional semantic search)
- sentence-transformers (optional)
- SHL Product Catalog (377 assessments)

## License

MIT