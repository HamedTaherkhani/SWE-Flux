from yt_dlp.extractor.common import InfoExtractor


HTML_FRAGMENT = '''<!-- comment <input type="hidden" name="phantom" value="boo"> -->
<form action="/login">
<input type="hidden" name="csrf_token" value="abc123">
<input type="text" name="username" value="ignored">
<input type="hidden" name="" value="missing_name">
<input type="submit" id="btn-submit" value="Send">
<input type="hidden" name="redirect" value="/home?next=1&amp;page=2">
<input type="checkbox" name="remember" value="1">
<input type="hidden" name="ref" value="">
<input type="HIDDEN" id="legacy_id" value="42">
<input type='hidden' name='quote_test' value='single_quote_attr'>
</form>'''


class TestExtractorHiddenInputsLoopStateQA:
    def test_extractor_hidden_inputs_loop_state_case(self):
        result = InfoExtractor._hidden_inputs(HTML_FRAGMENT)

        # Shape-only assertions; do not reveal mid-loop or final values.
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result)
