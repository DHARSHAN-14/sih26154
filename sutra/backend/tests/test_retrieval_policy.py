from __future__ import annotations
from app.retrieval.policy import decide, Route


class TestRetrievalPolicy:
    def test_route_a_small_source(self):
        d = decide(token_count=5000, threshold=25000)
        assert d.route == Route.A

    def test_route_b_large_source(self):
        d = decide(token_count=30000, threshold=25000)
        assert d.route == Route.B

    def test_route_b_multi_file(self):
        d = decide(token_count=1000, threshold=25000, file_count=3)
        assert d.route == Route.B

    def test_route_b_long_audio(self):
        d = decide(token_count=1000, threshold=25000, media_duration_sec=1500)
        assert d.route == Route.B

    def test_reason_populated(self):
        d = decide(token_count=5000, threshold=25000)
        assert d.reason
        assert "Route A" in d.reason
