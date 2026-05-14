from yt_dlp.utils._utils import parse_filesize


class TestLookupUnitTableNumValueRangeSuiteQA:
    def test_a(self):
        assert parse_filesize("0.1 TB") is not None

    def test_b(self):
        assert parse_filesize("0.5 GB") is not None

    def test_c(self):
        assert parse_filesize("1 B") is not None

    def test_d(self):
        assert parse_filesize("1.5 MiB") is not None

    def test_e(self):
        assert parse_filesize("2 KB") is not None

    def test_f(self):
        assert parse_filesize("5 MB") is not None

    def test_g(self):
        assert parse_filesize("10 GB") is not None

    def test_h(self):
        assert parse_filesize("50 KB") is not None

    def test_i(self):
        assert parse_filesize("100 bytes") is not None

    def test_j(self):
        assert parse_filesize("250 MB") is not None

    def test_k(self):
        assert parse_filesize("500 KB") is not None

    def test_l(self):
        assert parse_filesize("750 GB") is not None

    def test_m(self):
        assert parse_filesize("1024 bytes") is not None

    def test_n(self):
        assert parse_filesize("2048 KiB") is not None

    def test_o(self):
        assert parse_filesize("5000 MB") is not None

    def test_p(self):
        assert parse_filesize("10000 KB") is not None

    def test_q(self):
        assert parse_filesize("0.001 GB") is not None

    def test_r(self):
        assert parse_filesize("99999 KB") is not None
