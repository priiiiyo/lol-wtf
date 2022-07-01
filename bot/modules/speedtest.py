from logging import error as log_error
from threading import Thread

from speedtest import Speedtest
from telegram.ext import CommandHandler

from bot import dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    deleteMessage,
    sendMessage,
    sendPhoto,
)


def speedtest(update, context):
    speed = sendMessage("𝐑𝐮𝐧𝐧𝐢𝐧𝐠 𝐒𝐩𝐞𝐞𝐝 𝐓𝐞𝐬𝐭 . . . ", context.bot, update.message)
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    result = test.results.dict()
    string_speed = f"""
╭ ──🛰️ 𝐒𝐞𝐫𝐯𝐞𝐫 🛰️
├  🖥️ 𝐍𝐚𝐦𝐞 ⇢ <code>{result['server']['name']}</code>
├  🌍 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ⇢ <code>{result['server']['country']}, {result['server']['cc']}</code>
├  🪂 𝐒𝐩𝐨𝐧𝐬𝐨𝐫 ⇢ <code>{result['server']['sponsor']}</code>
├  🤖 𝐈𝐒𝐏 ⇢ <code>{result['client']['isp']}</code>
│
├  🎯 𝐒𝐩𝐞𝐞𝐝𝐓𝐞𝐬𝐭 𝐑𝐞𝐬𝐮𝐥𝐭𝐬 🎯
├  📤 𝐔𝐩𝐥𝐨𝐚𝐝 ⇢ <code>{speed_convert(result['upload'] / 8)}</code>
├  📥 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 ⇢ <code>{speed_convert(result['download'] / 8)}</code>
├  📊 𝐏𝐢𝐧𝐠 ⇢ <code>{result['ping']} ms</code>
╰ ─🔗 𝐈𝐒𝐏 𝐑𝐚𝐭𝐢𝐧𝐠 ⇢ <code>{result['client']['isprating']}</code>
"""
    try:
        path = test.results.share()
        pho = sendPhoto(text=string_speed, message=update.message, photo=path)
        Thread(
            target=auto_delete_message, args=(context.bot, update.message, pho)
        ).start()
        deleteMessage(context.bot, speed)
    except Exception as g:
        log_error(str(g))
        log_error("3. ")
        deleteMessage(context.bot, speed)
        reply_message = sendMessage(string_speed, context.bot, update.message)
        Thread(
            target=auto_delete_message,
            args=(update.message, reply_message),
        ).start()


def speed_convert(size, byte=True):
    """Hi human, you can't read bytes?"""
    if not byte:
        size = size / 8  # byte or bit ?
    power = 2**10
    zero = 0
    units = {
        0: "",
        1: "Kilobytes/s",
        2: "Megabytes/s",
        3: "Gigabytes/s",
        4: "Terabytes/s",
    }
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"


SPEED_HANDLER = CommandHandler(
    BotCommands.SpeedCommand,
    speedtest,
    filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
    run_async=True,
)

dispatcher.add_handler(SPEED_HANDLER)
