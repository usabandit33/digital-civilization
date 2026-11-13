"""Tests for Memory Record Schema"""

import unittest
from versioned_memory import MemoryRecord, VersionedMemoryStore


class TestMemorySchema(unittest.TestCase):
    """Smoke tests for memory record storage."""
    
    @classmethod
    def setUpClass(cls):
        """Setup: delete any test database from previous runs."""
        VersionedMemoryStore.cleanup()
        
    @classmethod
    def tearDownClass(cls):
        """Teardown: remove test artifacts."""
        import os
        if os.path.exists("memory.db"):
            os.remove("memory.db")
    
    def test_create_retrieve(self):
        """Test basic create and retrieve cycle."""
        r = MemoryRecord(
            content="This is a test memory entry",
            confidence=0.9,
            source="observation"
        )
        created_id = VersionedMemoryStore.store_record(r)
        
        assert created_id is not None, "Failed to store record"
        
        retrieved = VersionedMemoryStore.get_record(created_id)
        self.assertIsNotNone(retrieved, "Failed to retrieve record")
        self.assertEqual(retrieved.content, "This is a test memory entry")
        self.assertEqual(retrieved.confidence, 0.9)
    
    def test_confidence_filtering(self):
        """Test query with confidence threshold."""
        r1 = MemoryRecord(content="High confidence", confidence=0.95)
        r2 = MemoryRecord(content="Low confidence", confidence=0.5)
        
        VersionedMemoryStore.store_record(r1)
        VersionedMemoryStore.store_record(r2)
        
        high_conf_ids = VersionedMemoryStore.query(confidence__gte=0.8)
        self.assertIn(r1.id, high_conf_ids, "High-confidence record not found")
        self.assertNotIn(r2.id, high_conf_ids, "Low-confidence record found when it shouldn't be")


if __name__ == "__main__":
    # Run tests in-memory, don't modify actual file
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemorySchema)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Clean up database regardless of test outcome
    VersionedMemoryStore.cleanup()