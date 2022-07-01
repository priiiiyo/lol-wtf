from threading import Thread

from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.ext_utils.bot_utils import is_gdrive_link
from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage


def deletefile(update, context):
    reply_to = update.message.reply_to_message
    if len(context.args) == 1:
        link = context.args[0]
    elif reply_to:
        link = reply_to.text
    else:
        link = ""
    if is_gdrive_link(link):
        LOGGER.info(link)
        drive = gdriveTools.GoogleDriveHelper()
        msg = drive.deletefile(link)
    else:
        msg = (
            "Sᴇɴᴅ GDʀɪᴠᴇ Lɪɴᴋ Aʟᴏɴɢ Wɪᴛʜ Cᴏᴍᴍᴀɴᴅ Oʀ Bʏ Rᴇᴘʟʏɪɴɢ Tᴏ Tʜᴇ Lɪɴᴋ Bʏ Cᴏᴍᴍᴀɴᴅ"
        )
    reply_message = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, reply_message)
    ).start()


delete_handler = CommandHandler(
    command=BotCommands.DeleteCommand,
    callback=deletefile,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)
dispatcher.add_handler(delete_handler)
