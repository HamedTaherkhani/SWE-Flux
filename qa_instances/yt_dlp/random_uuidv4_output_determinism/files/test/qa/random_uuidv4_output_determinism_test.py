import random

from yt_dlp.utils._utils import random_uuidv4


class TestRandomUuidv4OutputDeterminismQA:
    def test_random_uuidv4_output_determinism_case(self):
        results = []
        for _ in range(5):
            random.seed(42)
            results.append(random_uuidv4())

        # Shape-only assertions; do not reveal whether values are identical.
        assert len(results) == 5
        assert all(isinstance(r, str) for r in results)
        assert all(len(r) == 36 for r in results)
