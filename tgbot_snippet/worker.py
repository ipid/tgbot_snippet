__all__ = ('Worker',)

import asyncio
import logging
from typing import Optional, List

import aiohttp

from .config import *
from .type_hint import *

# Snippet: The Worker class
class Worker:
    __slots__ = ('token', 'proxy', 'warm_up',
                 '_q', '_session', '_logger', '_loop', '_workers', '_timeout')

    def __init__(self, token: str,
                 proxy: Optional[str], warm_up: bool = True,
                 worker_num: int = DEFAULT_WORKER,
                 logger: logging.Logger = logging.getLogger('snippet.worker'),
                 sock_timeout: float = SOCK_TIMEOUT) -> None:
        """
        The Worker class provides A robust, asynchronous way to call Telegram API.
        :param token: Telegram bot token.
        :param proxy: Proxy url that has a format of http://<host>:<port>
        :param warm_up: When set to False, warming up of workers will be disabled.
        :param worker_num: The number of worker instances, which controls how many API calls can be handled simultaneously.
        :param logger: logging.Logger
        :param sock_timeout: Timeout for connection being built successfully. Default is 5-RTT(estimated).
        """

        self.token = token
        self.proxy = proxy
        self.warm_up = warm_up

        # _q is the task dispatching queue
        self._q = asyncio.Queue()
        # Cache the event loop instance
        self._loop = asyncio.get_event_loop()

        # lifecycle of session is the same as current worker
        conn = aiohttp.TCPConnector(limit=0, limit_per_host=0, keepalive_timeout=KEEP_ALIVE_TIMEOUT)
        self._session = aiohttp.ClientSession(connector=conn)

        # You may specify your own logger, or use the default version.
        self._logger = logger

        # Set timeout for requests
        assert sock_timeout > 0
        self._timeout = aiohttp.ClientTimeout(sock_connect=sock_timeout)

        # Store worker task instance for closing them.
        self._workers: List[asyncio.Task] = []
        for i in range(worker_num):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)

    '''
        Asynchronously receive method calling task, 
        send request to Telegram server, and return result.
    '''

    async def _worker(self, worker_id: int):
        """
        Worker to call API.
        :param worker_id: ID used for logging.
        :return: None
        """

        # Sometimes it takes time to send data to Telegram API server.
        # This brings tremendous delay to the very first request of a worker, because it takes 5-RTT
        # to connect to Telegram server.
        # Warm up to start an alive connection and avoid delay.
        if self.warm_up:
            self._logger.info('{} begin warming up'.format(worker_id))
            try:
                # Read robots.txt to keep connection with api.telegram.org,
                # and avoid API rate limit(in-doubt)
                async with self._session.get('https://api.telegram.org/robots.txt', proxy=self.proxy,
                                             timeout=self._timeout) as resp:
                    # Read full response to ensure connection is built
                    c = await resp.read()
                self._logger.info('{} warm up finished: resp len {}'.format(worker_id, len(c)))
            except Exception as e:
                self._logger.exception('{} Failed to warm up:\n{}'.format(worker_id, e))

        # Main loop of worker.
        # Worker get task from self._q, call specified API with param, and
        # return result by using asyncio.Future.
        while True:
            # Get task dispatched by call() function
            task: WorkerTask = await self._q.get()

            # Expand task tuple
            method, param, future = task

            # When aiohttp raise an exception or 'ok' field is set to False,
            # return None as the result
            res: Optional[JSON] = None
            try:
                async with self._session.post('https://api.telegram.org/bot{}/{}'.format(self.token, method),
                                              proxy=self.proxy, json=param, timeout=self._timeout) as resp:
                    res = await resp.json()

                    # Telegram server is assumed to return something like {
                    #     "ok": true, "result": ...
                    # }
                    if not res.get('ok'):
                        # Telegram API server returns error
                        # Error will be logged but won't be raised as exception

                        reason = ''

                        # Server sometimes give a description to the failure
                        if res.get('description'):
                            reason = ', due to: ' + res['description']

                        # Log that description if possible
                        self._logger.fatal('Call method `{}` failed{}'.format(method, reason))
                        res = None
                    else:
                        # Return the 'result' property
                        res = res['result']

            # Request is timeout or invalid JSON is received
            except Exception as e:
                self._logger.exception('\nException during calling {}:\n{}'.format(method, e))

            # When call_void is used, `future` will be None.
            if future is not None:
                # Return the result by save it into Future.
                future.set_result(res)

    # param is readonly so {} is okay to be the default value
    def call(self, method: str, param: JSON = {}) -> asyncio.Future:
        """
        Call specified Telegram API asynchronously with specified param.
        :param method: Name of the method.
        :param param: Param.
        :return: Wrapped in asyncio.Future, the 'result' part of server response if succeed. When failed, return None.
        """

        # Use Future to store response data to keep it asynchronous.
        future: asyncio.Future = self._loop.create_future()
        task: WorkerTask = (method, param, future)

        # Dispatch the task to a worker
        self._q.put_nowait(task)

        return future

    def call_void(self, method: str, param={}) -> None:
        """
        Call specified Telegram API asynchronously with specified param, but discard response.
        :param method: Name of the method.
        :param param: Param.
        :return: None
        """

        task: WorkerTask = (method, param, None)
        self._q.put_nowait(task)

    def close(self) -> None:
        """
        Stop all workers and clean the environment.
        :return: None
        """

        for task in self._workers:
            task.cancel()
        self._session.close()

    def __del__(self):
        self.close()
