import asyncio
import logging
from typing import Dict

from config_secret import *
from tgbot_snippet import *

async def main(token: str, proxy: str):
    w = Worker(token, proxy)
    q = asyncio.Queue()
    btn = DataButton(token, hash_length=10)
    asyncio.create_task(updater(w, q, allowed_updates=['message', 'callback_query']))

    while True:
        update = await q.get()
        if update.get('message'):
            msg = update['message']

            if msg.get('text', '') != '/button':
                print('receive invalid info:', msg.get('text', ''))
                continue

            w.call_void('sendMessage', {
                'chat_id': msg['chat']['id'], 'text': 'Test Buttons',
                'reply_to_message_id': msg['message_id'],
                'reply_markup': {'inline_keyboard': [
                    [btn('a', 'a'), btn('b', 'b')],
                    [btn('c', 'c')]
                ]}
            })
        elif update.get('callback_query'):
            query = update['callback_query']
            extra = {}
            data = btn.parse(query['data'])
            if data is not None:
                if data == 'c':
                    extra['show_alert'] = True

                w.call_void('answerCallbackQuery', {
                    'callback_query_id': query['id'],
                    'text': 'You clicked ' + data,
                    **extra
                })

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(token=IPID_MISC_BOT, proxy=PROXY_URL))
