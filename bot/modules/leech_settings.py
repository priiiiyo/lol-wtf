from os import mkdir
from os import path as ospath
from os import remove as osremove
from threading import Thread

from PIL import Image
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    AS_DOC_USERS,
    AS_DOCUMENT,
    AS_MEDIA_USERS,
    AUTO_DELETE_MESSAGE_DURATION,
    DB_URI,
    dispatcher,
)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_upload_message,
    editMessage,
    sendMarkup,
    sendMessage,
)


def getleechinfo(from_user):
    user_id = from_user.id
    name = from_user.full_name
    buttons = button_build.ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    if user_id in AS_DOC_USERS or user_id not in AS_MEDIA_USERS and AS_DOCUMENT:
        ltype = "DOCUMENT"
        buttons.sbutton("Sᴇɴᴅ As Mᴇᴅɪᴀ", f"leechset {user_id} med")
    else:
        ltype = "MEDIA"
        buttons.sbutton("Sᴇɴᴅ As Dᴏᴄᴜᴍᴇɴᴛ", f"leechset {user_id} doc")

    if ospath.exists(thumbpath):
        thumbmsg = "Exists"
        buttons.sbutton("Dᴇʟᴇᴛᴇ Tʜᴜᴍʙɴᴀɪʟ", f"leechset {user_id} thumb")
    else:
        thumbmsg = "Not Exists"

    if AUTO_DELETE_MESSAGE_DURATION == -1:
        buttons.sbutton("Cʟᴏsᴇ", f"leechset {user_id} close")

    button = InlineKeyboardMarkup(buttons.build_menu(1))

    text = (
        f"<u>Lᴇᴇᴄʜ Sᴇᴛᴛɪɴɢs ꜰᴏʀ <a href='tg://user?id={user_id}'>{name}</a></u>\n"
        f"Lᴇᴇᴄʜ Tʏᴘᴇ <b>{ltype}</b>\n"
        f"Cᴜsᴛᴏᴍ Tʜᴜᴍʙɴᴀɪʟ <b>{thumbmsg}</b>"
    )
    return text, button


def editLeechType(message, query):
    msg, button = getleechinfo(query.from_user)
    editMessage(msg, message, button)


def leechSet(update, context):
    msg, button = getleechinfo(update.message.from_user)
    choose_msg = sendMarkup(msg, context.bot, update.message, button)
    Thread(
        target=auto_delete_upload_message,
        args=(context.bot, update.message, choose_msg),
    ).start()


def setLeechType(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "doc":
        if user_id in AS_MEDIA_USERS:
            AS_MEDIA_USERS.remove(user_id)
        AS_DOC_USERS.add(user_id)
        if DB_URI is not None:
            DbManger().user_doc(user_id)
        query.answer(text="Your File Will Deliver As Document!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "med":
        if user_id in AS_DOC_USERS:
            AS_DOC_USERS.remove(user_id)
        AS_MEDIA_USERS.add(user_id)
        if DB_URI is not None:
            DbManger().user_media(user_id)
        query.answer(text="Your File Will Deliver As Media!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "thumb":
        path = f"Thumbnails/{user_id}.jpg"
        if ospath.lexists(path):
            osremove(path)
            if DB_URI is not None:
                DbManger().user_rm_thumb(user_id, path)
            query.answer(text="Thumbnail Removed!", show_alert=True)
            editLeechType(message, query)
        else:
            query.answer(text="Old Settings", show_alert=True)
    else:
        query.answer()
        try:
            query.message.delete()
            query.message.reply_to_message.delete()
        except Exception:
            pass


def setThumb(update, context):
    user_id = update.message.from_user.id
    reply_to = update.message.reply_to_message
    if reply_to is not None and reply_to.photo:
        path = "Thumbnails/"
        if not ospath.isdir(path):
            mkdir(path)
        photo_dir = reply_to.photo[-1].get_file().download()
        des_dir = ospath.join(path, f"{str(user_id)}.jpg")
        Image.open(photo_dir).convert("RGB").save(des_dir, "JPEG")
        osremove(photo_dir)
        if DB_URI is not None:
            DbManger().user_save_thumb(user_id, des_dir)
        msg = f"Cᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ sᴀᴠᴇᴅ ꜰᴏʀ {update.message.from_user.mention_html(update.message.from_user.first_name)}."
        reply_message = sendMessage(msg, context.bot, update.message)
    else:
        reply_message = sendMessage(
            "Rᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴛᴏ sᴀᴠᴇ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ.", context.bot, update.message
        )
    Thread(
        target=auto_delete_upload_message,
        args=(context.bot, update.message, reply_message),
    ).start()
    return reply_message


leech_set_handler = CommandHandler(
    BotCommands.LeechSetCommand,
    leechSet,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
set_thumbnail_handler = CommandHandler(
    BotCommands.SetThumbCommand,
    setThumb,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
but_set_handler = CallbackQueryHandler(setLeechType, pattern="leechset", run_async=True)

dispatcher.add_handler(leech_set_handler)
dispatcher.add_handler(but_set_handler)
dispatcher.add_handler(set_thumbnail_handler)
