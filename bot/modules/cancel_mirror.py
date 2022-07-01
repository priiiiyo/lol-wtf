from threading import Thread
from time import sleep

from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    OWNER_ID,
    QB_SEED,
    SUDO_USERS,
    dispatcher,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    MirrorStatus,
    getAllDownload,
    getDownloadByGid,
)
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    deleteMessage,
    sendMarkup,
    sendMessage,
)


def cancel_mirror(update, context):
    user_id = update.message.from_user.id
    if len(context.args) == 1:
        gid = context.args[0]
        dl = getDownloadByGid(gid)
        if not dl:
            reply_message = sendMessage(
                f"GID ⇢ <code>{gid}</code> Nᴏᴛ Fᴏᴜɴᴅ.", context.bot, update.message
            )
            Thread(
                target=auto_delete_message,
                args=(context.bot, update.message, reply_message),
            ).start()
            return reply_message
    elif update.message.reply_to_message:
        mirror_message = update.message.reply_to_message
        with download_dict_lock:
            keys = list(download_dict.keys())
            if mirror_message.message_id in keys:
                dl = download_dict[mirror_message.message_id]
            else:
                dl = None
        if not dl:
            reply_message = sendMessage(
                "Tʜɪs ɪs ɴᴏᴛ ᴀɴ ᴀᴄᴛɪᴠᴇ ᴛᴀsᴋ﹗", context.bot, update.message
            )
            Thread(
                target=auto_delete_message,
                args=(context.bot, update.message, reply_message),
            ).start()
            return reply_message
    elif len(context.args) == 0:
        msg = f"Rᴇᴘʟʏ ᴛᴏ ᴀɴ ᴀᴄᴛɪᴠᴇ <code>/{BotCommands.MirrorCommand}</code> ᴍᴇssᴀɢᴇ ᴡʜɪᴄʜ ᴡᴀs ᴜsᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴛʜᴇ ᴅᴏᴡɴʟᴏᴀᴅ ᴏʀ sᴇɴᴅ <code>/{BotCommands.CancelMirror} GID</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ɪᴛ﹗"
        reply_message = sendMessage(msg, context.bot, update.message)
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
        return reply_message

    if (
        OWNER_ID != user_id
        and dl.message.from_user.id != user_id
        and user_id not in SUDO_USERS
    ):
        reply_message = sendMessage(
            "Tʜɪs ᴛᴀsᴋ ɪs ɴᴏᴛ ꜰᴏʀ ʏᴏᴜ﹗", context.bot, update.message
        )
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
        return reply_message
    reply_message = ""
    if dl.status() == MirrorStatus.STATUS_ARCHIVING:
        reply_message = sendMessage(
            "Aʀᴄʜɪᴠᴀʟ ɪɴ Pʀᴏɢʀᴇss, Yᴏᴜ Cᴀɴ'ᴛ Cᴀɴᴄᴇʟ Iᴛ.", context.bot, update.message
        )
    elif dl.status() == MirrorStatus.STATUS_EXTRACTING:
        reply_message = sendMessage(
            "Exᴛʀᴀᴄᴛ ɪɴ Pʀᴏɢʀᴇss, Yᴏᴜ Cᴀɴ'ᴛ Cᴀɴᴄᴇʟ Iᴛ.", context.bot, update.message
        )
    elif dl.status() == MirrorStatus.STATUS_SPLITTING:
        reply_message = sendMessage(
            "Sᴘʟɪᴛ ɪɴ Pʀᴏɢʀᴇss, Yᴏᴜ Cᴀɴ'ᴛ Cᴀɴᴄᴇʟ Iᴛ.", context.bot, update.message
        )
    else:
        dl.download().cancel_download()
        Thread(
            target=deleteMessage,
            args=(context.bot, update.message, True),
        ).start()
    if reply_message != "":
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()


def cancel_all(status):
    gid = ""
    while dl := getAllDownload(status):
        if dl.gid() != gid:
            gid = dl.gid()
            dl.download().cancel_download()
            sleep(1)


def cancell_all_buttons(update, context):
    buttons = button_build.ButtonMaker()
    buttons.sbutton("Dᴏᴡɴʟᴏᴀᴅɪɴɢ", "canall down")
    buttons.sbutton("Uᴘʟᴏᴀᴅɪɴɢ", "canall up")
    if QB_SEED:
        buttons.sbutton("Uᴘʟᴏᴀᴅɪɴɢ", "canall seed")
    buttons.sbutton("Cʟᴏɴɪɴɢ", "canall clone")
    buttons.sbutton("Aʟʟ", "canall all")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup("Cʜᴏᴏsᴇ ᴛᴀsᴋs ᴛᴏ ᴄᴀɴᴄᴇʟ﹕ ", context.bot, update.message, button)


def cancel_all_update(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if CustomFilters._owner_query(user_id):
        query.answer()
        query.message.delete()
        cancel_all(data[1])
    else:
        query.answer(
            text="You don't have permission to use these buttons!", show_alert=True
        )


cancel_mirror_handler = CommandHandler(
    BotCommands.CancelMirror,
    cancel_mirror,
    filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user),
    run_async=True,
)

cancel_all_handler = CommandHandler(
    BotCommands.CancelAllCommand,
    cancell_all_buttons,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)

cancel_all_buttons_handler = CallbackQueryHandler(
    cancel_all_update, pattern="canall", run_async=True
)

dispatcher.add_handler(cancel_all_handler)
dispatcher.add_handler(cancel_mirror_handler)
dispatcher.add_handler(cancel_all_buttons_handler)
