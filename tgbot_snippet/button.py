__all__ = ('DataButton',)

from typing import Optional

from .config import *
from .type_hint import *
from .util import *

class DataButton:
    __slots__ = ('_secret_key', '_hash_length')

    def _get_hmac(self, data: str, key: str) -> str:
        """
        Get first HASH_LENGTH chars of base64-encoded HMAC digest.
        :param data: Data.
        :param key: Secret key.
        :return: The result.
        """
        return b64_hmac(data, key)[:self._hash_length]

    def __init__(self, secret_key: str, hash_length: int = HASH_LENGTH):
        """
        Provide a safe way to send and check data in inline button.
        :param secret_key: Secret key required by HMAC. Use bot's token is a good choice.
        :param hash_length: How much character should be used for hmac. The longer it is,
        the safer it will be; but message will have to be shorter.
        """
        self._secret_key = secret_key
        self._hash_length = hash_length

    def __call__(self, text: str, data: str) -> JSON:
        """
        InlineKeyButton object generator, which provide button data validation.
        Remember to use DataButton.parse to get the real data.
        :param text: The caption of button.
        :param data: Callback data.
        :return: JSON in dict.
        """
        if len(data.encode()) > BUTTON_DATA_MAX_LEN - self._hash_length:
            raise ValueError('data must not be longer than {}'.format(BUTTON_DATA_MAX_LEN - self._hash_length))
        hmac = self._get_hmac(data, self._secret_key)

        return {
            'text': text, 'callback_data': data + hmac
        }

    def parse(self, data_with_hmac: Optional[str]) -> Optional[str]:
        """
        Parse the data with hmac in user reply.
        According to Telegram API document, a user can return arbitrary data in a CallbackQuery.
        HMAC can ensure that the data is sent from server so that we can send sensitive data without
        store it in the server.
        :param data_with_hmac: If button sent with data_btn(), data field in CallbackQuery.
        :return: None if data is malformed or None, else the original data.
        """
        if data_with_hmac is None:
            return None
        if len(data_with_hmac) < self._hash_length:
            return None

        data, hmac = data_with_hmac[:-self._hash_length], data_with_hmac[-self._hash_length:]
        if hmac != self._get_hmac(data, self._secret_key):
            return None
        return data
