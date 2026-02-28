"""
Tests for FaceMatcher engine module.
"""

import json
import numpy as np
import pytest

from engines.facial_recognition.matcher import FaceMatcher, MatchResult


class TestMatchResult:
    def test_matched_property(self):
        assert MatchResult(student_id=1).matched is True
        assert MatchResult().matched is False

    def test_to_dict(self):
        r = MatchResult(student_id=5, student_name='Alice', confidence=0.82)
        d = r.to_dict()
        assert d['student_id'] == 5
        assert d['student_name'] == 'Alice'
        assert d['confidence'] == 0.82


class TestFaceMatcher:
    def _random_embedding(self):
        emb = np.random.randn(512).astype(np.float32)
        emb /= np.linalg.norm(emb)
        return emb

    def test_empty_cache_returns_no_match(self):
        matcher = FaceMatcher(threshold=0.4)
        result = matcher.match(self._random_embedding())
        assert result.matched is False

    def test_add_and_match(self):
        matcher = FaceMatcher(threshold=0.3)
        emb = self._random_embedding()
        matcher.add_face(42, 'Bob', emb)

        result = matcher.match(emb)
        assert result.matched is True
        assert result.student_id == 42
        assert result.student_name == 'Bob'
        assert result.confidence > 0.99  # same embedding

    def test_match_below_threshold(self):
        matcher = FaceMatcher(threshold=0.99)
        matcher.add_face(1, 'Alice', self._random_embedding())
        result = matcher.match(self._random_embedding())
        # Random embeddings should have low similarity
        assert result.matched is False

    def test_add_from_json_string(self):
        matcher = FaceMatcher(threshold=0.3)
        emb = self._random_embedding()
        json_str = json.dumps(emb.tolist())
        matcher.add_face(10, 'Charlie', json_str)
        assert matcher.known_count == 1
        result = matcher.match(emb)
        assert result.matched is True

    def test_add_from_list(self):
        matcher = FaceMatcher(threshold=0.3)
        emb = self._random_embedding()
        matcher.add_face(20, 'Diana', emb.tolist())
        assert matcher.known_count == 1

    def test_remove_face(self):
        matcher = FaceMatcher(threshold=0.3)
        matcher.add_face(1, 'Test', self._random_embedding())
        assert matcher.known_count == 1
        matcher.remove_face(1)
        assert matcher.known_count == 0

    def test_clear(self):
        matcher = FaceMatcher()
        for i in range(5):
            matcher.add_face(i, f'Person_{i}', self._random_embedding())
        assert matcher.known_count == 5
        matcher.clear()
        assert matcher.known_count == 0

    def test_best_match_among_multiple(self):
        matcher = FaceMatcher(threshold=0.3)
        target = self._random_embedding()
        # Add target
        matcher.add_face(1, 'Target', target)
        # Add unrelated
        matcher.add_face(2, 'Other', self._random_embedding())
        matcher.add_face(3, 'Another', self._random_embedding())

        result = matcher.match(target)
        assert result.student_id == 1   # should match target
        assert result.confidence > 0.9

    def test_invalid_embedding_shape(self):
        matcher = FaceMatcher()
        with pytest.raises(ValueError, match='512-d'):
            matcher.add_face(1, 'Bad', np.zeros(256))

    def test_match_all(self):
        matcher = FaceMatcher()
        emb = self._random_embedding()
        matcher.add_face(1, 'A', emb)
        matcher.add_face(2, 'B', self._random_embedding())

        results = matcher.match_all(emb, top_k=2)
        assert len(results) == 2
        assert results[0][0] == 1  # best match first

    def test_stats(self):
        matcher = FaceMatcher(threshold=0.5)
        matcher.add_face(10, 'X', self._random_embedding())
        stats = matcher.get_stats()
        assert stats['known_faces'] == 1
        assert stats['threshold'] == 0.5
        assert 10 in stats['face_ids']
