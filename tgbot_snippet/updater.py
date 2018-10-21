__all__ = ('updater',)

import asyncio

from .config import *
from .worker import *

async def updater(worker: Worker, queue: asyncio.Queue,
                  sleep_on_fail: int = SLEEP_ON_FAIL, timeout: int = UPDATE_TIMEOUT, **kwargs):
    update_offset = 0
    param = {
        'timeout': timeout, 'offset': None, **kwargs
    }

    while True:
        # Update offset without create new object
        param['offset'] = update_offset

        # Get updates
        updates = await worker.call('getUpdates', param)

        # If update has failed(may reaches rate limit), sleep to bypass the limitation.
        if updates is None:
            await asyncio.sleep(sleep_on_fail)
            continue

        for update in updates:
            # Dispatch update by putting into the queue.
            # Use blocking put to support queue with element limit.
            await queue.put(update)
            update_offset = update['update_id'] + 1
