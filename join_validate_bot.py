import asyncio
import logging
from time import time
from typing import Dict, Any, Optional, Tuple

from config_secret import *
from tgbot_snippet import *

WELCOME_TEXT = '''欢迎 @{}！

请于 {} 秒内点击以下按钮，超时则您将会被移除出群：'''

BUTTON_TEXT = '( )  我不是机器人。'
WELCOME_AGAIN_TEXT = '验证通过。'
KICK_NOTICE_TEXT = '用户 @{} 超时未验证，已移除。'

KICK_TIMEOUT = 10
BAN_UNTIL = 60

REMOVE_RESTRICT = {
    'can_send_messages': True,
    'can_send_media_messages': True,
    'can_send_other_messages': True,
    'can_add_web_page_previews': True
}

def not_robot_btn_data(chat_id: str, user_id: str) -> str:
    return 'notrbt:{}:{}'.format(chat_id, user_id)

def parse_btn_data(data: Optional[str]) -> Optional[Tuple[str, str]]:
    if data is None:
        return None

    l = data.split(':')
    if len(l) != 3 or l[0] != 'notrbt':
        return None

    return l[1], l[2]  # May be use

class NewbieHandler:
    def __init__(self, btn: DataButton, w: Worker):
        self.btn = btn
        self.w = w
        self._kick_timers: Dict[Tuple[str, str], asyncio.Task] = {}

    def cancel_kick_timer(self, chat_id: str, user_id: str, message_id: str):
        timer: Optional = self._kick_timers.get((chat_id, user_id))
        if timer is None:
            return

        timer.cancel()
        del self._kick_timers[chat_id, user_id]

        self.w.call_void('restrictChatMember', {
            'chat_id': chat_id, 'user_id': int(user_id),
            'until_date': time() + 5,
            **REMOVE_RESTRICT
        })
        # Delete the button
        self.w.call_void('deleteMessage', {
            'chat_id': chat_id, 'message_id': int(message_id)
        })

    async def handler(self, chat_id: str, user_id: str, username: str):
        print('Restrict:', await self.w.call('restrictChatMember', {
            'chat_id': chat_id, 'user_id': int(user_id),
            'until_date': int(time() + 86400 * 365 * 2)
        }))

        await self.w.call('sendMessage', {
            'chat_id': chat_id,
            'text': WELCOME_TEXT.format(username, KICK_TIMEOUT),
            'reply_markup': {'inline_keyboard': [
                [self.btn(BUTTON_TEXT, not_robot_btn_data(chat_id, user_id))]
            ]}
        })

        timer = asyncio.create_task(
            self.kick_timer(chat_id, user_id, username)
        )
        self._kick_timers[chat_id, user_id] = timer

    async def kick_timer(self, chat_id: str, user_id: str,
                         username: str,
                         delay: float = float(KICK_TIMEOUT)):
        print('Begin kick timing for @{}'.format(username))

        try:
            await asyncio.sleep(delay + 1)

            self.w.call_void('kickChatMember', {
                'chat_id': chat_id, 'user_id': user_id,
                'until_date': time() + BAN_UNTIL
            })
            self.w.call_void('sendMessage', {
                'chat_id': chat_id, 'text': KICK_NOTICE_TEXT.format(username)
            })
            del self._kick_timers[chat_id, user_id]

        except asyncio.CancelledError:
            print('@{} passed validation'.format(username))

async def main(token: str, proxy: str):
    w = Worker(token=token, proxy=proxy, worker_num=16)
    q = asyncio.Queue()
    asyncio.create_task(updater(w, q, allowed_updates=['message', 'callback_query']))
    btn = DataButton(token)
    nbh = NewbieHandler(btn, w)

    while True:
        update: Dict[str, Any] = await q.get()

        for newbie in update.get('message', {}).get('new_chat_members', []):
            asyncio.create_task(nbh.handler(
                str(update['message']['chat']['id']), str(newbie['id']), newbie["username"]
            ))

        ids = parse_btn_data(btn.parse(update.get('callback_query', {}).get('data', '')))

        if ids is not None:
            # ids can be trust
            chat_id, user_id = ids

            if str(update['callback_query']['from']['id']) == user_id:
                nbh.cancel_kick_timer(
                    chat_id, user_id,
                    str(update['callback_query']['message']['message_id'])
                )
                w.call_void('answerCallbackQuery', {
                    'callback_query_id': update['callback_query']['id'],
                    'text': WELCOME_AGAIN_TEXT,
                    'show_alert': True
                })
            else:
                # Other group member clicked that button
                w.call_void('answerCallbackQuery', {
                    'callback_query_id': update['callback_query']['id'],
                    'text': ''
                })

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(token=IPID_MISC_BOT, proxy=PROXY_URL))
