from telegram.helpers import escape_markdown


class TestHelpersEscapeMarkdownDirectOutputQA:
    def test_escape_markdown_direct_output_case(self):
        source_text = r"A_B[C](D)~E`F>G#H+I-J=K|L{M}.N! and slash \\ end"
        escaped_text = escape_markdown(source_text, version=2)

        assert isinstance(escaped_text, str)
        assert len(escaped_text) > len(source_text)
        assert escaped_text.count("\\") >= source_text.count("\\")
        assert "and slash" in escaped_text
