# Vector Database Analysis - RAG Phase 3+

## Current Database Architecture

**No vector database** is present. The system uses:

### **SQLite (via SQLAlchemy ORM)**

**Current tables:**
1. **Prospect** - Contact information (name, email, phone, state, etc.)
2. **Conversation** - Intake sessions and their lifecycle
3. **Message** - Transcript messages (role, content, timestamps)
4. **IntakeSummaryRecord** - Structured intake summaries with JSON payloads
5. **LLMCallRecord** - Audit trail for LLM API calls (request/response metadata)
6. **FollowUpTask** - Scheduled follow-up tasks with templates
7. **AuditLog** - Append-only audit events

### Why No Vector Database?

This is a **supervision-first legal intake system**, not a RAG (Retrieval-Augmented Generation) application. The architecture is intentionally simple:

**Current approach:**
- ✓ Keyword-based classification (stub mode)
- ✓ LLM-based classification with structured JSON output (real mode)
- ✓ Deterministic cross-practice rule scanning
- ✓ Full conversation transcripts stored as text

**Vector databases would be needed for:**
- ❌ Semantic search across historical cases (not in scope)
- ❌ Case similarity matching (not implemented)
- ❌ RAG-based question answering (not needed - LLM gets full transcript)
- ❌ Document embedding/retrieval (no document storage yet)

### Current LLM Usage

The LLM receives the **full conversation transcript** directly:
```python
# From app/services/summary_generator.py
summary = await generate_summary(
    session,
    conversation_id,
    prospect,
    transcript_text  # Full text passed to LLM
)
```

No retrieval needed because:
1. Conversations are short (intake is focused)
2. Context window is large (128k tokens for Llama 3.1 70B)
3. No historical context required (each intake is independent)
4. Compliance requires explicit, auditable inputs

### If You Need Vector Search

Future use cases that might require a vector database:

1. **Case precedent search**: "Find similar TCPA cases"
2. **Attorney knowledge base**: RAG over internal legal documentation
3. **Evidence matching**: Semantic search across collected evidence
4. **Duplicate detection**: Find if prospect already contacted firm

**Recommended additions** (if needed):
- **Embedding model**: `text-embedding-3-small` or `sentence-transformers`
- **Vector DB**: Qdrant (self-hosted), Chroma (local), or pgvector (PostgreSQL extension)
- **New table**: `EmbeddedContent` with vector column and metadata

### Summary

**Current state**: ✅ Pure relational database (SQLite)
**Vector database**: ❌ Not present
**Need for vectors**: ⚠️ Not required for current scope (Phase 1-2)
**Future consideration**: ✓ Could add for case search/RAG in Phase 3+

---

## Future Phase 3+ Vector Database Implementation Plan

### Use Cases for Vector Search

#### 1. Case Precedent Search
**Goal**: Find similar historical cases to provide context to attorneys

**Implementation**:
- Embed `IntakeSummaryRecord.fact_pattern` field
- Store embeddings with metadata (practice_area, outcome, attorney_notes)
- Query: "Find top 5 similar TCPA cases with robocall patterns"

**Schema**:
```python
class CaseEmbedding(Base):
    id: str
    summary_id: str  # FK to IntakeSummaryRecord
    embedding: Vector(1536)  # text-embedding-3-small dimension
    practice_area: PracticeArea
    confidence_score: float
    outcome: str | None  # "accepted", "rejected", "settled"
    created_at: datetime
```

#### 2. Attorney Knowledge Base (RAG)
**Goal**: Answer attorney questions using firm's internal documentation

**Implementation**:
- Chunk legal documents/precedents into passages
- Embed each chunk with context metadata
- RAG flow: question → retrieve relevant chunks → LLM synthesis

**Schema**:
```python
class KnowledgeChunk(Base):
    id: str
    document_id: str
    chunk_text: str
    embedding: Vector(1536)
    document_type: str  # "case_law", "firm_memo", "statute"
    practice_areas: list[PracticeArea]
    chunk_index: int
    created_at: datetime
```

#### 3. Evidence Similarity Matching
**Goal**: Match collected evidence against known evidence patterns

**Implementation**:
- Embed evidence descriptions from successful cases
- Compare new evidence against historical patterns
- Suggest missing evidence based on similar cases

#### 4. Duplicate Detection
**Goal**: Identify if prospect has already contacted the firm

**Implementation**:
- Embed prospect first message + contact info
- Semantic search for similar intakes
- Flag potential duplicates for attorney review

### Recommended Vector Database Options

#### Option 1: **Qdrant** (Recommended for Phase 3)
**Pros**:
- Self-hosted (compliance-friendly)
- Excellent filtering (practice_area, date ranges)
- Python client with async support
- Hybrid search (dense + sparse vectors)

**Cons**:
- Additional infrastructure to manage
- Requires Redis for distributed mode

**Setup**:
```bash
docker run -p 6333:6333 qdrant/qdrant
pip install qdrant-client
```

#### Option 2: **pgvector** (PostgreSQL Extension)
**Pros**:
- Integrates with existing SQLAlchemy models
- Single database for relational + vector data
- ACID compliance for audit requirements

**Cons**:
- Requires PostgreSQL migration from SQLite
- Slower than specialized vector DBs at scale

**Setup**:
```sql
CREATE EXTENSION vector;
ALTER TABLE intake_summaries ADD COLUMN embedding vector(1536);
CREATE INDEX ON intake_summaries USING ivfflat (embedding vector_cosine_ops);
```

#### Option 3: **Chroma** (Local Development)
**Pros**:
- Zero-setup for local development
- Built-in embedding support
- Great for prototyping

**Cons**:
- Not production-ready for high scale
- Limited filtering capabilities

**Setup**:
```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection("intake_cases")
```

### Embedding Model Selection

#### Recommended: **text-embedding-3-small** (OpenAI)
- **Dimensions**: 1536
- **Cost**: $0.02 / 1M tokens
- **Quality**: Excellent for legal text
- **Speed**: Fast API response

#### Alternative: **sentence-transformers/all-MiniLM-L6-v2**
- **Dimensions**: 384
- **Cost**: Free (self-hosted)
- **Quality**: Good for general similarity
- **Speed**: Fast local inference

### Implementation Architecture

```python
# app/services/vector_search.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

class VectorSearchService:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = "intake_cases"

    async def index_summary(self, summary_id: str, fact_pattern: str, metadata: dict):
        """Embed and index a case summary"""
        embedding = await get_embedding(fact_pattern)
        self.client.upsert(
            collection_name=self.collection,
            points=[{
                "id": summary_id,
                "vector": embedding,
                "payload": metadata
            }]
        )

    async def find_similar_cases(
        self,
        query: str,
        practice_area: PracticeArea | None = None,
        limit: int = 5
    ) -> list[dict]:
        """Find similar cases by semantic search"""
        query_embedding = await get_embedding(query)
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            query_filter={
                "must": [{"key": "practice_area", "match": {"value": practice_area.value}}]
            } if practice_area else None,
            limit=limit
        )
        return results
```

### Compliance Considerations

**Critical requirements for vector search in legal system**:

1. **Auditability**:
   - Log all vector queries and results
   - Store embedding model version with each vector
   - Maintain lineage: which cases were retrieved and why

2. **Determinism**:
   - Cache embeddings (don't re-embed on every search)
   - Version control for embedding models
   - Reproducible retrieval results

3. **Privacy**:
   - Embeddings may leak PII information
   - Consider differential privacy for sensitive cases
   - Ensure vector DB has same security as relational DB

4. **Human Review**:
   - Vector search results are **suggestions only**
   - Attorney must review all retrieved context
   - Never auto-accept based on similarity score

### Migration Path from Phase 2 → Phase 3

**Step 1: Add vector infrastructure**
```bash
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
```

**Step 2: Update dependencies**
```toml
# pyproject.toml
dependencies = [
  # ... existing deps
  "qdrant-client>=1.7.0",
  "openai>=1.0.0",  # for embeddings API
]
```

**Step 3: Backfill existing cases**
```python
# scripts/backfill_embeddings.py
async def backfill_case_embeddings():
    summaries = await session.execute(select(IntakeSummaryRecord))
    for summary in summaries.scalars():
        await vector_service.index_summary(
            summary.id,
            summary.fact_pattern,
            metadata={
                "practice_area": summary.primary_practice_area,
                "confidence": summary.primary_confidence,
                "created_at": summary.created_at.isoformat()
            }
        )
```

**Step 4: Add search endpoint**
```python
# app/api/routes_search.py
@router.get("/cases/similar")
async def find_similar_cases(
    query: str,
    practice_area: PracticeArea | None = None,
    limit: int = 5
) -> list[SimilarCaseResult]:
    results = await vector_service.find_similar_cases(query, practice_area, limit)
    # Log search for audit
    await write_audit(session, "system", "case_search", "vector_search", results)
    return results
```

### Cost Estimation

**Assumptions**:
- 1000 intakes/month
- Average fact_pattern: 200 tokens
- Embedding model: text-embedding-3-small

**Monthly costs**:
- Initial embedding: 1000 × 200 tokens × $0.02/1M = $0.004
- Search queries: 500 queries/month × 50 tokens × $0.02/1M = $0.0005
- **Total**: ~$0.005/month (negligible)

**Infrastructure**:
- Qdrant self-hosted: $0 (Docker container)
- Qdrant Cloud: $25/month (managed, 1GB vectors)
- PostgreSQL + pgvector: $0 (if already using Postgres)

### Testing Strategy

**Unit tests**:
```python
# tests/test_vector_search.py
def test_embedding_consistency():
    """Same text should produce same embedding"""
    emb1 = await get_embedding("robocall case")
    emb2 = await get_embedding("robocall case")
    assert np.allclose(emb1, emb2, atol=1e-6)

def test_similarity_relevance():
    """Similar cases should rank higher than dissimilar"""
    index_case("TCPA robocall case about debt collection")
    index_case("FDCPA credit reporting dispute")

    results = search("unwanted phone calls about debt")
    assert results[0].practice_area == PracticeArea.TCPA
```

**Integration tests**:
- Test full RAG pipeline with real LLM
- Validate retrieved context improves classification
- Ensure compliance boundaries remain intact

### Next Steps

**Phase 3 implementation order**:
1. Choose vector DB (recommend Qdrant)
2. Add embedding service
3. Backfill existing cases
4. Build search API endpoints
5. Update attorney dashboard with "Similar Cases" panel
6. Monitor accuracy and refine retrieval

**Phase 4 (RAG)**:
1. Ingest firm knowledge base (case law, memos)
2. Implement hybrid search (semantic + keyword)
3. Build attorney Q&A interface
4. Add citation/source tracking

---

**Document Status**: Planning document for future phases
**Last Updated**: 2026-06-13
**Owner**: AI Intake V1 Architecture Team
