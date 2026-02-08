"""Unit tests for matching service helpers."""

import pytest

from app.services.matching_service import _distance_to_score


@pytest.mark.unit
class TestDistanceToScore:
    def test_identical_vectors(self) -> None:
        # Cosine distance 0 → score 1.0
        assert _distance_to_score(0.0) == 1.0

    def test_opposite_vectors(self) -> None:
        # Cosine distance 2 → score 0.0
        assert _distance_to_score(2.0) == 0.0

    def test_mid_distance(self) -> None:
        # Cosine distance 1 → score 0.5
        assert _distance_to_score(1.0) == 0.5

    def test_small_distance(self) -> None:
        score = _distance_to_score(0.2)
        assert 0.89 < score < 0.91  # ~0.9

    def test_clamped_above_two(self) -> None:
        # Should never happen, but clamp to 0.0
        assert _distance_to_score(3.0) == 0.0

    def test_negative_distance(self) -> None:
        # Should clamp to 1.0
        assert _distance_to_score(-0.5) == 1.0
