from yt_dlp.utils._utils import parse_resolution


class TestParseResolutionDuPairCoverageSuiteQA:
    def test_a(self):
        parse_resolution(None)

    def test_b(self):
        parse_resolution("1920x1080")

    def test_c(self):
        parse_resolution("1280x720")

    def test_d(self):
        parse_resolution("640x480")

    def test_e(self):
        parse_resolution("3840×2160")

    def test_f(self):
        parse_resolution("100,200")

    def test_g(self):
        parse_resolution("nothing")

    def test_h(self):
        parse_resolution("1080p")

    def test_i(self):
        parse_resolution("720i")

    def test_j(self):
        parse_resolution("480P")

    def test_k(self):
        parse_resolution("360I")

    def test_l(self):
        parse_resolution("4k")

    def test_m(self):
        parse_resolution("8K")

    def test_n(self):
        parse_resolution("4K")

    def test_o(self):
        parse_resolution("video.mp4")

    def test_p(self):
        parse_resolution("")

    def test_q(self):
        parse_resolution("abc")

    def test_r(self):
        parse_resolution("xyz")
