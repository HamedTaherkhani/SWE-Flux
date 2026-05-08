from yt_dlp.utils._utils import parse_m3u8_attributes


class TestParseM3u8AttributesLoopValueInvariantSuiteQA:
    def test_a(self):
        parse_m3u8_attributes("BANDWIDTH=1280000")

    def test_b(self):
        parse_m3u8_attributes("PROGRAM-ID=1")

    def test_c(self):
        parse_m3u8_attributes('BANDWIDTH=2500000,CODECS="mp4a.40.2,avc1.4d401e"')

    def test_d(self):
        parse_m3u8_attributes("RESOLUTION=720x480")

    def test_e(self):
        parse_m3u8_attributes('NAME="English"')

    def test_f(self):
        parse_m3u8_attributes('TYPE=AUDIO,GROUP-ID="audio"')

    def test_g(self):
        parse_m3u8_attributes('LANGUAGE="en"')

    def test_h(self):
        parse_m3u8_attributes("TARGETDURATION=10")

    def test_i(self):
        parse_m3u8_attributes('METHOD=AES-128,URI="https://example.com/key.bin"')

    def test_j(self):
        parse_m3u8_attributes("BANDWIDTH=500000,RESOLUTION=640x360,FRAME-RATE=30.000")

    def test_k(self):
        parse_m3u8_attributes('TYPE=VIDEO,GROUP-ID="video",NAME="720p"')

    def test_l(self):
        parse_m3u8_attributes('BANDWIDTH=1000000,AUDIO="audio",VIDEO="video"')

    def test_m(self):
        parse_m3u8_attributes('CODECS="avc1.640015,mp4a.40.5"')

    def test_n(self):
        parse_m3u8_attributes('CHARACTERISTICS="public.accessibility.transcribes-spoken-dialog"')

    def test_o(self):
        parse_m3u8_attributes('INSTREAM-ID="CC1"')

    def test_p(self):
        parse_m3u8_attributes('CLOSED-CAPTIONS="cc"')

    def test_q(self):
        parse_m3u8_attributes('BANDWIDTH=600000,RESOLUTION=854x480,CODECS="mp4a.40.2,avc1.640015"')

    def test_r(self):
        parse_m3u8_attributes("AUTOSELECT=YES,DEFAULT=YES")
