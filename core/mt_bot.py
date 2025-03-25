import asyncio
from config import CONFIG
from bot.bot import Bot
from bot.event import Event, EventType
from bot.handler import (MessageHandler,
                         CommandHandler,
                         BotButtonCommandHandler,
                         UnknownCommandHandler)

from datetime import datetime

__all__ = ("mybot", "start_bot", "send_msg")

mybot = Bot(token=CONFIG["bot"]["token"], api_url_base=CONFIG["bot"]["url"])


def message_cb(bot, event):
    print(event.from_chat)
    bot.send_text(chat_id=event.from_chat, text="repairnet bot is running")


def send_msg(chat_id, msg, parse_mode=None):
    bot = Bot(token=CONFIG["bot"]["token"], api_url_base=CONFIG["bot"]["url"])
    bot.send_text(chat_id=chat_id, text=msg, parse_mode=parse_mode)


def start_bot():
    mybot.dispatcher.add_handler(MessageHandler(callback=message_cb))
    mybot.start_polling()
    mybot.idle()


if __name__ == "__main__":
    send_msg(chat_id=CONFIG["bot"]["admin_chat"], msg=f'repairnet bot test {datetime.now()}')

