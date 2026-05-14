from yt_dlp.utils._utils import mimetype2ext


class TestMimetype2ExtSubtypeValueSetSuiteQA:
    def test_a(self): mimetype2ext("video/mp4")
    def test_b(self): mimetype2ext("audio/mpeg")
    def test_c(self): mimetype2ext("application/dash+xml")
    def test_d(self): mimetype2ext("application/json")
    def test_e(self): mimetype2ext("image/webp")
    def test_f(self): mimetype2ext("audio/x-flac")
    def test_g(self): mimetype2ext("video/webm")
    def test_h(self): mimetype2ext("audio/webm")
    def test_i(self): mimetype2ext("image/jpeg")
    def test_j(self): mimetype2ext("video/x-matroska")
    def test_k(self): mimetype2ext("application/vnd.apple.mpegurl")
    def test_l(self): mimetype2ext("audio/ogg")
    def test_m(self): mimetype2ext("image/png")
    def test_n(self): mimetype2ext("image/gif")
    def test_o(self): mimetype2ext("image/svg+xml")
    def test_p(self): mimetype2ext("video/avi")
    def test_q(self): mimetype2ext("application/zip")
    def test_r(self): mimetype2ext("audio/aac")
