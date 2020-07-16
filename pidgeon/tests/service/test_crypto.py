from pidgeon.service.crypto import SymCrypto
from pytest import fixture, raises
from random import randint, choice
from string import ascii_letters


class TestSymmetricCryptoService:
    @fixture
    def service(self):
        return SymCrypto()

    def test_encrypt_decrypt(self, service):
        scenarios = [
            (service.keygen(), self._get_random_string())
            for i in range(17)
        ]

        for key, message in scenarios:
            encrypted = service.encrypt(key, message)
            decrypted = service.decrypt(key, encrypted)

            assert decrypted
            assert decrypted == message

    def _get_random_string(self):
        return "".join([
            choice(ascii_letters) for i in range(1, randint(1, 100))
        ])
