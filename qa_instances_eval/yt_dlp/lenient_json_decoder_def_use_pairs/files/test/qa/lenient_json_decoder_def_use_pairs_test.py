from yt_dlp.utils._utils import LenientJSONDecoder


JSON_INPUT = '{"a": 1, "b": [2, 3'


class TestLenientJsonDecoderDefUsePairsQA:
    def test_lenient_json_decoder_def_use_pairs_case(self):
        decoder = LenientJSONDecoder(close_objects=2)
        result = decoder.decode(JSON_INPUT)

        # Shape-only assertion; do not reveal the def-use pairs.
        assert isinstance(result, dict)
