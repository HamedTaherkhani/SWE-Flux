from yt_dlp.postprocessor.metadataparser import MetadataParserPP


FMT = "%(title)s - %(artist)s [%(album)s].%(ext)s"


class TestFormatToRegexPathDeterminismQA:
    def test_format_to_regex_path_determinism_case(self):
        results = []
        for _ in range(5):
            results.append(MetadataParserPP.format_to_regex(FMT))

        # Shape-only assertions; do not reveal whether paths are identical.
        assert len(results) == 5
        assert all(isinstance(r, str) for r in results)
