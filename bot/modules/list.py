from threading import Thread
from time import time

from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    editMessage,
    sendMarkup,
    sendMessage,
)


def list_buttons(update, context):
    user_id = update.message.from_user.id
    if len(context.args) == 0:
        reply_message = sendMessage(
            "Sᴇɴᴅ ᴀ sᴇᴀʀᴄʜ ᴋᴇʏ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴄᴏᴍᴍᴀɴᴅ.", context.bot, update.message
        )
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
        return reply_message
    buttons = button_build.ButtonMaker()
    buttons.sbutton("Fᴏʟᴅᴇʀs", f"types {user_id} folders")
    buttons.sbutton("Fɪʟᴇs", f"types {user_id} files")
    buttons.sbutton("Bᴏᴛʜ", f"types {user_id} both")
    buttons.sbutton("Cᴀɴᴄᴇʟ", f"types {user_id} cancel")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup("Cʜᴏᴏsᴇ ᴏᴘᴛɪᴏɴ ᴛᴏ ʟɪsᴛ﹕ ", context.bot, update.message, button)


def select_type(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    msg = query.message
    key = msg.reply_to_message.text.split(" ", maxsplit=1)[1]
    data = query.data
    data = data.split()
    if user_id != int(data[1]):
        return query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "cancel":
        query.answer()
        reply_message = editMessage("ʟɪsᴛ ʜᴀs ʙᴇᴇɴ ᴄᴀɴᴄᴇʟᴇᴅ﹗", msg)
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
        return reply_message
    query.answer()
    item_type = data[2]
    editMessage(f"Sᴇᴀʀᴄʜɪɴɢ Fᴏʀ <i>{key}</i> Pʟᴇᴀsᴇ Wᴀɪᴛ \n Tʏᴘᴇ ⇢ {item_type}", msg)
    Thread(target=_list_drive, args=(key, msg, item_type)).start()


def _list_drive(key, bmsg, item_type):
    LOGGER.info(f"listing: {key}")
    gdrive = GoogleDriveHelper()
    msg, button = gdrive.drive_list(key, isRecursive=True, itemType=item_type)
    msg += f"\n Tʏᴘᴇ ⇢ {item_type}"
    msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - bmsg.date.timestamp())}\n"
    if button:
        editMessage(msg, bmsg, button)
    else:
        editMessage(
            f"Nᴏ ʀᴇsᴜʟᴛ ꜰᴏᴜɴᴅ ꜰᴏʀ <i>{key}</i> \n Tʏᴘᴇ ⇢ {item_type} {msg}", bmsg
        )


list_handler = CommandHandler(
    BotCommands.ListCommand,
    list_buttons,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
list_type_handler = CallbackQueryHandler(select_type, pattern="types", run_async=True)
dispatcher.add_handler(list_handler)
dispatcher.add_handler(list_type_handler)
