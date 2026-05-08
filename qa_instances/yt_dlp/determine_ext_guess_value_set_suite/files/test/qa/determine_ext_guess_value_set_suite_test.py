from yt_dlp.utils._utils import determine_ext


class TestDetermineExtGuessValueSetSuiteQA:
    def test_a(self):
        determine_ext("http://example.com/file.mp4")

    def test_b(self):
        determine_ext("http://other.com/clip.mp4")

    def test_c(self):
        determine_ext("https://example.com/movie.webm")

    def test_d(self):
        determine_ext("https://stream.io/audio.mp3")

    def test_e(self):
        determine_ext("https://stream.io/song.mp3")

    def test_f(self):
        determine_ext("https://example.com/clip.flv")

    def test_g(self):
        determine_ext("http://cdn.example.net/clip.avi")

    def test_h(self):
        determine_ext("https://files.com/data.json")

    def test_i(self):
        determine_ext("https://cdn.com/video.mkv")

    def test_j(self):
        determine_ext("https://example.com/audio.aac")

    def test_k(self):
        determine_ext("https://example.com/file.mov")

    def test_l(self):
        determine_ext("https://example.com/clip.wmv")

    def test_m(self):
        determine_ext("https://example.com/foo/bar.m3u8")

    def test_n(self):
        determine_ext("https://example.com/foo/bar.ogg/")

    def test_o(self):
        determine_ext("http://example.com/segment.ts")

    def test_p(self):
        determine_ext("http://example.com/file.webp")

    def test_q(self):
        determine_ext("http://example.com/picture.jpg")

    def test_r(self):
        determine_ext("http://example.com/clip.f4m")
