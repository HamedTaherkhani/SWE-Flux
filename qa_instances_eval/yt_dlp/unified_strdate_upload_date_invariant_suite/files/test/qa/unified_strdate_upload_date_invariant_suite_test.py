from yt_dlp.utils._utils import unified_strdate


class TestUnifiedStrdateUploadDateInvariantSuiteQA:
    def test_a(self):
        unified_strdate("2014-08-12")

    def test_b(self):
        unified_strdate("2017/05/03")

    def test_c(self):
        unified_strdate("2019.07.04.")

    def test_d(self):
        unified_strdate("15 March 2020")

    def test_e(self):
        unified_strdate("5 Jan 2018")

    def test_f(self):
        unified_strdate("April 22 2021")

    def test_g(self):
        unified_strdate("Aug 30 2015")

    def test_h(self):
        unified_strdate("2016-11-22 13:45:00")

    def test_i(self):
        unified_strdate("2018-01-31T08:00:00")

    def test_j(self):
        unified_strdate("2022-06-15T12:34:56Z")

    def test_k(self):
        unified_strdate("01.02.2019")

    def test_l(self):
        unified_strdate("31/12/2010")

    def test_m(self):
        unified_strdate("Mon, 27 May 2024 12:34:56 GMT")

    def test_n(self):
        unified_strdate("July 4 2026")

    def test_o(self):
        unified_strdate("Feb 28 2024")

    def test_p(self):
        unified_strdate("2013-09-10 23:59:59.123456")

    def test_q(self):
        unified_strdate("03/04/2020")

    def test_r(self):
        unified_strdate("7 December 2017")
