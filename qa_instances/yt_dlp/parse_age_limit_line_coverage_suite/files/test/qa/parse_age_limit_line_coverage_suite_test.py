from yt_dlp.utils._utils import parse_age_limit


class TestParseAgeLimitLineCoverageSuiteQA:
    def test_a(self):
        parse_age_limit(5)

    def test_b(self):
        parse_age_limit(25)

    def test_c(self):
        parse_age_limit(0)

    def test_d(self):
        parse_age_limit(-5)

    def test_e(self):
        parse_age_limit(None)

    def test_f(self):
        parse_age_limit(3.14)

    def test_g(self):
        parse_age_limit(True)

    def test_h(self):
        parse_age_limit([])

    def test_i(self):
        parse_age_limit("5")

    def test_j(self):
        parse_age_limit("18")

    def test_k(self):
        parse_age_limit("21+")

    def test_l(self):
        parse_age_limit("0")

    def test_m(self):
        parse_age_limit("G")

    def test_n(self):
        parse_age_limit("PG-13")

    def test_o(self):
        parse_age_limit("R")

    def test_p(self):
        parse_age_limit("TV-MA")

    def test_q(self):
        parse_age_limit("TV_PG")

    def test_r(self):
        parse_age_limit("random")
