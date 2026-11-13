# Versioned Memory Record Schema

A structured, versioned schema for durable memory records that includes provenance tracking and confidence scoring. Designed to prevent knowledge drift and enable verification of what agents remember.

## Core Fields

```python
{
    "id": str,      # Deterministic fingerprint: normalized content hash (SHA-256)
    "version": int,  # Schema version for migrations (defaults 1)
    "source": str,   # Origin: "observation", "retrieval", "user-provided", "inferred"
    "timestamp": int,  # Unix epoch when created/last-modified
    "confidence": float,  # 0.0-1.0 belief strength (1 = absolute)
    "retention_days": int,      # Auto-expiry for safety-critical data
    "content": str | dict,       # The actual memory content
    "raw_reference": str | None,    # URL/file path for traceability (if external source)
}
```

### Field Purpose

| Field | Type | Why It Matters |
|-------|------|----------------|
| `id` | `str` | Deduplication key: content is hashed to prevent duplicate storage |
| `confidence` | `0.0-1.0` | Higher values = fewer retractions needed; 0.5 is "likely but check" |
| `retention_days` | `int` | Safety net for claims needing periodic verification (e.g., external facts) |
| `raw_reference` | `str` or None | Provable traceability: can we revisit the source? |

## Usage Examples

### Creating a Record

```python
from versioned_memory import MemoryRecord, SourceType

record = MemoryRecord(
    content="User prefers Python 3.14+",
    confidence=0.95,        # High belief — personal observation
    raw_reference=None,     # No external source to verify
    retention_days=None,    # Personal facts don't auto-expire
)

# Or for retrieved facts:
record = MemoryRecord(
    content="Ice floats because it's ~9% less dense than water",
    confidence=0.8,         # Lower — inferred from external text
    source="retrieval",      # Trackability matters here
    raw_reference="https://hyperphysics.phy-astronomy.gsu.edu/",
    retention_days=365,     # External claims should be periodically verified
)
```

### Accessing with Confidence Filtering

```python
high_confidence = db.query(confinence__gte=0.9)  # "Treat as fact"
review_needed = db.query(confidence__lt=0.8)  # "Schedule verification"
verified_data = db.query(retention_days=None).all()  # Never expires
```

## Schema Migrations

Use the `version` field to track schema changes:

- v1: Core fields only (id, version, source, timestamp, confidence)
- v2: Added `raw_reference` for traceability
- v3: Added `retention_days` for safety-critical data expiry

To migrate: store with `version=n`, read with `__eq__` logic that compares versions.

## Verification Policy

| Confidence | Action Required |
|------------|-----------------|
| ≥ 0.95 | Treat as fact; accept unless contradicted |
| 0.75–0.94 | Accept but flag for periodic review (if `retention_days` set) |
| < 0.75 | Do not act on without external confirmation |

## Related Inventions

- `idempotent-complete/` — Ensure memory writes don't cause side effects
- `local-status/` — Query memory via API for other agents
