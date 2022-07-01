from threading import Thread

from telegram.ext import CommandHandler

from bot import AUTHORIZED_CHATS, DB_URI, LEECH_LOG, SUDO_USERS, dispatcher
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage


def authorize(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
        if user_id in AUTHORIZED_CHATS:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Aᴜᴛʜᴏʀɪᴢᴇᴅ 😲"
        elif DB_URI is not None:
            msg = DbManger().user_auth(user_id)
            AUTHORIZED_CHATS.add(user_id)
        else:
            AUTHORIZED_CHATS.add(user_id)
            with open("authorized_chats.txt", "a") as file:
                file.write(f"{user_id}\n")
                msg = "Usᴇʀ 𝐀𝐮𝐭𝐡𝐨𝐫𝐢𝐳𝐞𝐝 ✅"
    elif reply_message:
        # Trying to authorize someone by replying
        user_id = reply_message.from_user.id
        if user_id in AUTHORIZED_CHATS:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Aᴜᴛʜᴏʀɪᴢᴇᴅ 😲"
        elif DB_URI is not None:
            msg = DbManger().user_auth(user_id)
            AUTHORIZED_CHATS.add(user_id)
        else:
            AUTHORIZED_CHATS.add(user_id)
            with open("authorized_chats.txt", "a") as file:
                file.write(f"{user_id}\n")
                msg = "Usᴇʀ Aᴜᴛʜᴏʀɪᴢᴇᴅ ✅"
    else:
        # Trying to authorize a chat
        chat_id = update.effective_chat.id
        if chat_id in AUTHORIZED_CHATS:
            msg = "Cʜᴀᴛ Aʟʀᴇᴀᴅʏ Aᴜᴛʜᴏʀɪᴢᴇᴅ 😲"
        elif DB_URI is not None:
            msg = DbManger().user_auth(chat_id)
            AUTHORIZED_CHATS.add(chat_id)
        else:
            AUTHORIZED_CHATS.add(chat_id)
            with open("authorized_chats.txt", "a") as file:
                file.write(f"{chat_id}\n")
                msg = "Cʜᴀᴛ Aᴜᴛʜᴏʀɪᴢᴇᴅ ✅"
    replymessage = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


def unauthorize(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
        if user_id in AUTHORIZED_CHATS:
            if DB_URI is not None:
                msg = DbManger().user_unauth(user_id)
            else:
                msg = "Usᴇʀ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ 😁"
            AUTHORIZED_CHATS.remove(user_id)
        else:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ 😲"
    elif reply_message:
        # Trying to authorize someone by replying
        user_id = reply_message.from_user.id
        if user_id in AUTHORIZED_CHATS:
            if DB_URI is not None:
                msg = DbManger().user_unauth(user_id)
            else:
                msg = "Usᴇʀ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ 😁"
            AUTHORIZED_CHATS.remove(user_id)
        else:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ  😲"
    else:
        # Trying to unauthorize a chat
        chat_id = update.effective_chat.id
        if chat_id in AUTHORIZED_CHATS:
            if DB_URI is not None:
                msg = DbManger().user_unauth(chat_id)
            else:
                msg = "Cʜᴀᴛ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ 😁"
            AUTHORIZED_CHATS.remove(chat_id)
        else:
            msg = "Cʜᴀᴛ Aʟʀᴇᴀᴅʏ Uɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ 😲"
    if DB_URI is None:
        with open("authorized_chats.txt", "a") as file:
            file.truncate(0)
            for i in AUTHORIZED_CHATS:
                file.write(f"{i}\n")
    replymessage = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


def addleechlog(update, context):
    # Trying to add a user in leech logs
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
        if user_id in LEECH_LOG:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Aᴅᴅᴇᴅ Iɴ Lᴇᴇᴄʜ Lᴏɢs 😲"
        elif DB_URI is not None:
            msg = DbManger().addleech_log(user_id)
            LEECH_LOG.add(user_id)
        else:
            LEECH_LOG.add(user_id)
            with open("leech.txt", "a") as file:
                file.write(f"{user_id}\n")
                msg = "Usᴇʀ Aᴅᴅᴇᴅ Iɴ Lᴇᴇᴄʜ Lᴏɢs ✅"
    elif reply_message:
        # Trying to add someone by replying
        user_id = reply_message.from_user.id
        if user_id in LEECH_LOG:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Exɪsᴛ Iɴ Lᴇᴇᴄʜ Lᴏɢs 😲"
        elif DB_URI is not None:
            msg = DbManger().addleech_log(user_id)
            LEECH_LOG.add(user_id)
        else:
            LEECH_LOG.add(user_id)
            with open("leech.txt", "a") as file:
                file.write(f"{user_id}\n")
                msg = "Usᴇʀ Aᴅᴅᴇᴅ Iɴ Lᴇᴇᴄʜ Lᴏɢs ✅"
    else:
        # Trying to add a chat in leech logs
        chat_id = update.effective_chat.id
        if chat_id in LEECH_LOG:
            msg = "Cʜᴀᴛ Aʟʀᴇᴀᴅʏ Aᴅᴅᴇᴅ Iɴ Lᴇᴇᴄʜ Lᴏɢs 😲"
        elif DB_URI is not None:
            msg = DbManger().addleech_log(chat_id)
            LEECH_LOG.add(chat_id)
        else:
            LEECH_LOG.add(chat_id)
            with open("leech.txt", "a") as file:
                file.write(f"{chat_id}\n")
                msg = "Cʜᴀᴛ Aᴅᴅᴇᴅ Iɴ Lᴇᴇᴄʜ Lᴏɢs ✅"
    replymessage = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


def rmleechlog(update, context):
    # Trying to remove a user from leech log
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
        if user_id in LEECH_LOG:
            if DB_URI is not None:
                msg = DbManger().rmleech_log(user_id)
            else:
                msg = "Usᴇʀ Rᴇᴍᴏᴠᴇᴅ Fʀᴏᴍ Lᴇᴇᴄʜ Lᴏɢs 😁"
            LEECH_LOG.remove(user_id)
        else:
            msg = "Usᴇʀ Dᴏᴇs Nᴏᴛ Exɪsᴛ Iɴ Lᴇᴇᴄʜ Lᴏɢs 😲"
    elif reply_message:
        # Trying to remove someone by replying
        user_id = reply_message.from_user.id
        if user_id in LEECH_LOG:
            if DB_URI is not None:
                msg = DbManger().rmleech_log(user_id)
            else:
                msg = "Usᴇʀ Rᴇᴍᴏᴠᴇᴅ Fʀᴏᴍ Lᴇᴇᴄʜ Lᴏɢs 😁"
            LEECH_LOG.remove(user_id)
        else:
            msg = "Usᴇʀ Dᴏᴇs Nᴏᴛ Exɪsᴛ Iɴ Lᴇᴇᴄʜ Lᴏɢs 😲"
    else:
        # Trying to remove a chat from leech log
        chat_id = update.effective_chat.id
        if chat_id in LEECH_LOG:
            if DB_URI is not None:
                msg = DbManger().rmleech_log(chat_id)
            else:
                msg = "Cʜᴀᴛ Rᴇᴍᴏᴠᴇᴅ Fʀᴏᴍ Lᴇᴇᴄʜ Lᴏɢs 😁"
            LEECH_LOG.remove(chat_id)
        else:
            msg = "Cʜᴀᴛ Dᴏᴇs Nᴏᴛ Exɪsᴛ Iɴ Lᴇᴇᴄʜ Lᴏɢs 😲"
    if DB_URI is None:
        with open("leech.txt", "a") as file:
            file.truncate(0)
            for i in LEECH_LOG:
                file.write(f"{i}\n")
    replymessage = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


def addSudo(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
        if user_id in SUDO_USERS:
            msg = "Aʟʀᴇᴀᴅʏ Sᴜᴅᴏ 😲"
        elif DB_URI is not None:
            msg = DbManger().user_addsudo(user_id)
            SUDO_USERS.add(user_id)
        else:
            SUDO_USERS.add(user_id)
            with open("sudo_users.txt", "a") as file:
                file.write(f"{user_id}\n")
                msg = "Pʀᴏᴍᴏᴛᴇᴅ ᴀs Sᴜᴅᴏ ✅"
    elif reply_message:
        # Trying to authorize someone by replying
        user_id = reply_message.from_user.id
        if user_id in SUDO_USERS:
            msg = "Usᴇʀ Aʟʀᴇᴀᴅʏ Sᴜᴅᴏ 😲"
        elif DB_URI is not None:
            msg = DbManger().user_addsudo(user_id)
            SUDO_USERS.add(user_id)
        else:
            SUDO_USERS.add(user_id)
            with open("sudo_users.txt", "a") as file:
                file.write(f"{user_id}\n")
                msg = "Pʀᴏᴍᴏᴛᴇᴅ ᴀs Sᴜᴅᴏ ✅"
    else:
        msg = "Gɪᴠᴇ ID ᴏʀ Rᴇᴘʟʏ Tᴏ ᴍᴇssᴀɢᴇ ᴏꜰ ᴡʜᴏᴍ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ Pʀᴏᴍᴏᴛᴇ. 😲"
    replymessage = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


def removeSudo(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
        if user_id in SUDO_USERS:
            msg = (
                DbManger().user_rmsudo(user_id)
                if DB_URI is not None
                else "Usᴇʀ Dᴇᴍᴏᴛᴇᴅ Sᴜᴄᴄᴇssꜰᴜʟʟʏ 😁"
            )
            SUDO_USERS.remove(user_id)
        else:
            msg = "Nᴏᴛ sᴜᴅᴏ ᴜsᴇʀ ᴛᴏ ᴅᴇᴍᴏᴛᴇ 😲"
    elif reply_message:
        user_id = reply_message.from_user.id
        if user_id in SUDO_USERS:
            msg = (
                DbManger().user_rmsudo(user_id)
                if DB_URI is not None
                else "Usᴇʀ Dᴇᴍᴏᴛᴇᴅ Sᴜᴄᴄᴇssꜰᴜʟʟʏ 😁"
            )
            SUDO_USERS.remove(user_id)
        else:
            msg = "Nᴏᴛ sᴜᴅᴏ ᴜsᴇʀ ᴛᴏ ᴅᴇᴍᴏᴛᴇ 😲"
    else:
        msg = "Gɪᴠᴇ ID ᴏʀ Rᴇᴘʟʏ Tᴏ ᴍᴇssᴀɢᴇ ᴏꜰ ᴡʜᴏᴍ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ Rᴇᴍᴏᴠᴇ. 😲😲"
    if DB_URI is None:
        with open("sudo_users.txt", "a") as file:
            file.truncate(0)
            for i in SUDO_USERS:
                file.write(f"{i}\n")
    replymessage = sendMessage(msg, context.bot, update.message)
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


def sendAuthChats(update, context):
    user = sudo = leechlog = ""
    user += "\n".join(f"<code>{uid}</code>" for uid in AUTHORIZED_CHATS)
    sudo += "\n".join(f"<code>{uid}</code>" for uid in SUDO_USERS)
    leechlog += "\n".join(f"<code>{uid}</code>" for uid in LEECH_LOG)
    replymessage = sendMessage(
        f"Aᴜᴛʜᴏʀɪᴢᴇᴅ Cʜᴀᴛ𝘀: \n{user}\nSᴜᴅᴏ Usᴇʀs: \n{sudo}\nLᴇᴇᴄʜ Lᴏɢ: \n{leechlog}",
        context.bot,
        update.message,
    )
    Thread(
        target=auto_delete_message, args=(context.bot, update.message, replymessage)
    ).start()
    return replymessage


send_auth_handler = CommandHandler(
    command=BotCommands.AuthorizedUsersCommand,
    callback=sendAuthChats,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)
authorize_handler = CommandHandler(
    command=BotCommands.AuthorizeCommand,
    callback=authorize,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)
unauthorize_handler = CommandHandler(
    command=BotCommands.UnAuthorizeCommand,
    callback=unauthorize,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)
addsudo_handler = CommandHandler(
    command=BotCommands.AddSudoCommand,
    callback=addSudo,
    filters=CustomFilters.owner_filter,
    run_async=True,
)
removesudo_handler = CommandHandler(
    command=BotCommands.RmSudoCommand,
    callback=removeSudo,
    filters=CustomFilters.owner_filter,
    run_async=True,
)
addleechlog_handler = CommandHandler(
    command=BotCommands.AddleechlogCommand,
    callback=addleechlog,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)
rmleechlog_handler = CommandHandler(
    command=BotCommands.RmleechlogCommand,
    callback=rmleechlog,
    filters=CustomFilters.owner_filter | CustomFilters.sudo_user,
    run_async=True,
)

dispatcher.add_handler(send_auth_handler)
dispatcher.add_handler(authorize_handler)
dispatcher.add_handler(unauthorize_handler)
dispatcher.add_handler(addsudo_handler)
dispatcher.add_handler(removesudo_handler)
dispatcher.add_handler(addleechlog_handler)
dispatcher.add_handler(rmleechlog_handler)
