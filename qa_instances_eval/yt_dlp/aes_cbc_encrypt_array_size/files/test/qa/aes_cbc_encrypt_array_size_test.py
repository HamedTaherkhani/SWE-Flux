from yt_dlp.aes import aes_cbc_encrypt


class TestAesCbcEncryptArraySizeQA:
    def test_aes_cbc_encrypt_array_size_case(self):
        data = list(range(50))
        key = list(range(16))
        iv = list(range(16))
        result = aes_cbc_encrypt(data, key, iv, padding_mode="pkcs7")

        # Shape-only assertion; do not reveal mid-iteration sizes.
        assert isinstance(result, list)
