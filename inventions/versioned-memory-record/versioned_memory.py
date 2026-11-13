"""Versioned Memory Record — Schema & Storage"""

import hashlib
import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class MemoryRecord:
    """Single versioned memory record with provenance tracking."""
    content: str
    confidence: float = 1.0
    source: str = "observation"
    
    @property
    def raw_reference(self) -> str | None:
        return self._references.get("url")

    # Schema v2+ requires these fields
    retention_days: int = None
    version: int = 1
    
    _references: dict = field(default_factory=dict)


class VersionedMemoryStore:
    """SQLite-backed memory storage with schema migrations."""
    
    DB_PATH = "memory.db"
    SCHEMA_VERSION = 2  # Current active schema
    MIN_SCHEMA_VERSION = 1
    
    @classmethod
    def migrate_table(cls, conn):
        """Ensure table structure matches current schema version."""
        cursor = conn.cursor()
        
        # Create base table if not exists (SQLite doesn't support CREATE IF NOT EXISTS)
        check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_records'"
        cursor.execute(check_query)
        
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE memory_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL UNIQUE,
                    version INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL DEFAULT 'observation',
                    timestamp INTEGER NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0
                )
            """)
        
        # v2 upgrade: add raw_reference (nullable) and retention_days columns
        if cls.SCHEMA_VERSION > cls.MIN_SCHEMA_VERSION:
            cursor.execute("""
                ALTER TABLE memory_records ADD COLUMN IF NOT EXISTS raw_reference TEXT;
                ALTER TABLE memory_records ADD COLUMN IF NOT EXISTS retention_days INTEGER;
            """)
        
        # v3 upgrade (reserved for future): confidence threshold columns, trust_chain jsonb
        pass
    
    @classmethod
    def store_record(cls, record: MemoryRecord) -> int | None:
        """Store a memory record with proper schema versioning."""
        conn = sqlite3.connect(cls.DB_PATH, timeout=5.0)
        
        try:
            cls.migrate_table(conn)
            
            cursor = conn.cursor()
            fingerprint = hashlib.sha256(
                f"{record.content}:{record.source}".encode("utf-8")
            ).hexdigest()[:16]  # Deterministic dedup key
            
            if record.raw_reference:
                cursor.execute("""
                    INSERT OR REPLACE INTO memory_records 
                    (fingerprint, version, source, timestamp, confidence,
                     raw_reference, retention_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    fingerprint,
                    cls.SCHEMA_VERSION,
                    record.source,
                    int(timezone.now().timestamp()),
                    record.confidence,
                    record.raw_reference,
                    record.retention_days if record.retention_days else None,
                ))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO memory_records 
                    (fingerprint, version, source, timestamp, confidence, retention_days)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    fingerprint,
                    cls.SCHEMA_VERSION,
                    record.source,
                    int(timezone.now().timestamp()),
                    record.confidence,
                    record.retention_days if record.retention_days else None,
                ))
            
            new_id = cursor.lastrowid
        
        finally:
            conn.close()
        
        return new_id
