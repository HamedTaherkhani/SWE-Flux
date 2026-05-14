from yt_dlp.utils._utils import _sanitize_path_parts


class TestSanitizePathPartsLoopValueInvariantSuiteQA:
    def test_a(self):
        _sanitize_path_parts(["a", "b", "c"])

    def test_b(self):
        _sanitize_path_parts(["..", "a"])

    def test_c(self):
        _sanitize_path_parts(["foo", "bar", "baz"])

    def test_d(self):
        _sanitize_path_parts(["..", "..", "a"])

    def test_e(self):
        _sanitize_path_parts(["a", "b", ".."])

    def test_f(self):
        _sanitize_path_parts(["..", "..", ".."])

    def test_g(self):
        _sanitize_path_parts(["a", "..", "b"])

    def test_h(self):
        _sanitize_path_parts(["a", "..", "..", "b"])

    def test_i(self):
        _sanitize_path_parts(["a", "."])

    def test_j(self):
        _sanitize_path_parts(["..", "a", ".."])

    def test_k(self):
        _sanitize_path_parts(["", "a"])

    def test_l(self):
        _sanitize_path_parts(["a/b", "c"])

    def test_m(self):
        _sanitize_path_parts([".", "a", ""])

    def test_n(self):
        _sanitize_path_parts(["abc.", "def"])

    def test_o(self):
        _sanitize_path_parts(["a", ".", "b"])

    def test_p(self):
        _sanitize_path_parts(["foo bar ", "y"])

    def test_q(self):
        _sanitize_path_parts(["<file>", "x"])

    def test_r(self):
        _sanitize_path_parts(["...", "x"])
