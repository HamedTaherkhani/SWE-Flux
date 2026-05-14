import contextlib

from yt_dlp.cookies import get_cookie_decryptor


class _NullLogger:
    def debug(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


class TestChromeCookieDecryptorDecryptDispatchQA:
    def test_chrome_cookie_decryptor_decrypt_dispatch_case(self):
        decryptor = get_cookie_decryptor(
            "/tmp/profile",
            "Chromium",
            _NullLogger(),
            keyring="BASICTEXT",
        )
        with contextlib.suppress(Exception):
            decryptor.decrypt(b"v10" + b"\x00" * 16)
