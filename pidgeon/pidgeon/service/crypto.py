from base64 import b64encode, b64decode
from nacl.secret import SecretBox
from nacl.utils import random
from pidgeon.framework.constants import ENCODING
from pidgeon.framework.component.service import Service


NONCE_SIZE = SecretBox.NONCE_SIZE


class SymCrypto(Service):
    def encrypt(self, key: str, message: str) -> str:
        box = self._get_secret_box(key)
        plaintext = message.encode(ENCODING)
        nonce = random(NONCE_SIZE)
        ciphertext = box.encrypt(plaintext, nonce)
        ciphertext_b64 = b64encode(ciphertext)

        return ciphertext_b64.decode(ENCODING)

    def decrypt(self, key: str, ciphertext: str) -> str:
        box = self._get_secret_box(key)
        ciphertext_bytes = b64decode(ciphertext)
        plaintext = box.decrypt(ciphertext_bytes)

        return plaintext.decode(ENCODING)

    @staticmethod
    def keygen(size: int = SecretBox.KEY_SIZE) -> str:
        return b64encode(random(size)).decode(ENCODING)

    def _get_secret_box(self, key: str) -> SecretBox:
        return SecretBox(b64decode(key))
