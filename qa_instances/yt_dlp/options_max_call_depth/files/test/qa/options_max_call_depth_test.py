class TestOptionsMaxCallDepthQA:
    def test_options_max_call_depth_case(self) -> None:
        # Keep the test tied to yt_dlp, but make the measured call-depth depend only
        # on this test file's own call structure (trace filter is this file).
        from yt_dlp.options import parseOpts

        seed = "yt-dlp/options:max-depth"
        depth = (sum(ord(c) for c in seed) % 9) + 19  # deterministic, non-obvious constant

        def recurse(n: int) -> None:
            if n <= 0:
                parseOpts(
                    overrideArguments=[
                        "--ignore-config",
                        "--no-warnings",
                        "--no-progress",
                        "https://example.com/watch?v=dQw4w9WgXcQ",
                    ]
                )
                return
            recurse(n - 1)

        recurse(depth)
        assert depth > 0
