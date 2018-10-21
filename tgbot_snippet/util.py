__all__ = ('b64_hmac',)

from base64 import b64encode
from hashlib import sha256
import hmac

def b64_hmac(msg: str, key: str):
    h = hmac.new(key.encode(), msg.encode(), sha256)
    return b64encode(h.digest()).decode()
