from base64 import b64encode, b64decode
from nacl.secret import SecretBox
from nacl.utils import random


ENCODING = "UTF-8"
NONCE_SIZE = SecretBox.NONCE_SIZE


def encrypt(key: str, message: str) -> str:
    box = _get_secret_box(key)
    plaintext = message.encode(ENCODING)
    nonce = random(NONCE_SIZE)
    ciphertext = box.encrypt(plaintext, nonce)
    ciphertext_b64 = b64encode(ciphertext)

    return ciphertext_b64.decode(ENCODING)


def decrypt(key: str, ciphertext: str) -> str:
    box = _get_secret_box(key)
    ciphertext_bytes = b64decode(ciphertext)
    plaintext = box.decrypt(ciphertext_bytes)

    return plaintext.decode(ENCODING)


def _get_secret_box(key: str) -> SecretBox:
    return SecretBox(b64decode(key))
