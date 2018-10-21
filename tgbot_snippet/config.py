__all__ = ('DEFAULT_WORKER', 'SOCK_TIMEOUT', 'SLEEP_ON_FAIL', 'UPDATE_TIMEOUT', 'HASH_LENGTH',
           'BUTTON_DATA_MAX_LEN', 'KEEP_ALIVE_TIMEOUT')

"""
Maybe 8 worker is enough for normal cases.(in doubt)
"""
DEFAULT_WORKER = 8

"""
Maximum RTT to Telegram server, may go through one proxy
"""
MAX_API_RTT = 0.6

"""
Worst-case connect timeout: 5-RTT
Including:
    - TCP Handshake (1-RTT)
    - TLS 1.2 Handshake (2-RTT)
    - Unexpected cases (1-RTT)
"""
SOCK_TIMEOUT = MAX_API_RTT * 5

"""
Time for a connection to keep alive.
Can't be set to a extremely large value because epoll/select API doesn't allow it.
"""
KEEP_ALIVE_TIMEOUT = 86400 * 3

"""
Default value on how many seconds should updater wait until next getUpdates.
"""
SLEEP_ON_FAIL = 3

"""
Default update timeout.
"""
UPDATE_TIMEOUT = 30

"""
Default hash length to validate integrity.
"""
HASH_LENGTH = 8

BUTTON_DATA_MAX_LEN = 64
