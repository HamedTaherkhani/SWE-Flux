from yt_dlp.utils._utils import js_to_json


class TestJsToJsonDirectOutputQA:
    def test_js_to_json_direct_output_case(self):
        source_code = r'''/* config */
{
    id: 0xCAFE,
    perm: 020,
    user: undefined,
    host: void 0,
    path: "C:\x41bcB",
    note: 'a\nb\tc\xFF',
    when: new Date("2024-03-15"),
    n: parseInt("--42--"),
    items: Array("a", "b", 7),
    extras: [1, 2, 3,],
}'''

        result = js_to_json(source_code)

        assert isinstance(result, str)
        assert len(result) > 0
        assert ":" in result
