from threading import Thread
from time import time

from telegram import InlineKeyboardMarkup, ParseMode
from telegram.ext import CommandHandler

from bot import (
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
    BOT_PM,
    CHANNEL_USERNAME,
    FSUB,
    FSUB_CHANNEL_ID,
    LOGGER,
    dispatcher,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_time,
    is_gdrive_link,
    is_gdtot_link,
    new_thread,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.mirror_utils.download_utils.direct_link_generator import (
    appdrive,
    drivebuzz_dl,
    drivefire_dl,
    droplink_dl,
    gadrive_dl,
    gdtot,
    gplinks_dl,
    hubdrive_dl,
    jiodrive_dl,
    katdrive_dl,
    kolop_dl,
    sharerpw_dl,
)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    auto_delete_reply_message,
    auto_delete_upload_message,
    deleteMessage,
    sendMarkup,
    sendMessage,
)


def _count(message, bot):
    if FSUB:
        try:
            user = bot.get_chat_member(f"{FSUB_CHANNEL_ID}", message.from_user.id)
            LOGGER.info(user.status)
            if user.status not in ("member", "creator", "administrator", "supergroup"):
                if message.from_user.username:
                    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.username}</a>'
                else:
                    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
                buttons = ButtonMaker()
                chat_u = CHANNEL_USERNAME.replace("@", "")
                buttons.buildbutton("ðð» CHANNEL LINK ðð»", f"https://t.me/{chat_u}")
                help_msg = f"Dá´á´Ê {uname},\nYá´á´ É´á´á´á´ á´á´ á´á´ÉªÉ´ á´Ê CÊá´É´É´á´Ê á´á´ á´sá´ Bá´á´ \n\nCÊÉªá´á´ á´É´ á´Êá´ Êá´Êá´á´¡ Bá´á´á´á´É´ á´á´ á´á´ÉªÉ´ á´Ê CÊá´É´É´á´Ê."
                reply_message = sendMarkup(
                    help_msg, bot, message, InlineKeyboardMarkup(buttons.build_menu(2))
                )
                Thread(
                    target=auto_delete_message, args=(bot, message, reply_message)
                ).start()
                return reply_message
        except Exception:
            pass
    if BOT_PM and message.chat.type != "private":
        try:
            msg1 = f"LÉªÉ´á´ Aá´á´á´á´"
            send = bot.sendMessage(
                message.from_user.id,
                text=msg1,
            )
            send.delete()
        except Exception as e:
            LOGGER.warning(e)
            if message.from_user.username:
                uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.username}</a>'
            else:
                uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            buttons = ButtonMaker()
            buttons.buildbutton(
                "ðð» START BOT ðð»", f"https://t.me/{bot.get_me().username}?start=start"
            )
            help_msg = f"Dá´á´Ê {uname},\nYá´á´ É´á´á´á´ á´á´ sá´á´Êá´ á´Êá´ Êá´á´ á´sÉªÉ´É¢ á´Êá´ Êá´Êá´á´¡ Êá´á´á´á´É´.  \n\nIá´s É´á´á´á´á´á´ á´á´ Êá´á´ á´á´É´ sá´É´á´ Êá´á´Ê MÉªÊÊá´Ê/CÊá´É´á´/Lá´á´á´Êá´á´ FÉªÊá´s ÉªÉ´ BOT PM. \n\nCÊÉªá´á´ á´É´ á´Êá´ Êá´Êá´á´¡ Êá´á´á´á´É´ á´á´ sá´á´Êá´ á´Êá´ Êá´á´ á´É´á´ TÊÊ AÉ¢á´ÉªÉ´."
            reply_message = sendMarkup(
                help_msg, bot, message, InlineKeyboardMarkup(buttons.build_menu(2))
            )
            Thread(
                target=auto_delete_message, args=(bot, message, reply_message)
            ).start()
            return reply_message
    args = message.text.split(maxsplit=1)
    reply_to = message.reply_to_message
    link = ""
    if len(args) > 1:
        link = args[1].strip()
        if message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    is_gdtot = is_gdtot_link(link)
    is_driveapp = True if "driveapp" in link else False
    is_appdrive = True if "appdrive" in link else False
    is_hubdrive = True if "hubdrive" in link else False
    is_drivehub = True if "drivehub" in link else False
    is_kolop = True if "kolop" in link else False
    is_drivebuzz = True if "drivebuzz" in link else False
    is_gdflix = True if "gdflix" in link else False
    is_drivesharer = True if "drivesharer" in link else False
    is_drivebit = True if "drivebit" in link else False
    is_drivelink = True if "drivelink" in link else False
    is_katdrive = True if "katdrive" in link else False
    is_gadrive = True if "gadrive" in link else False
    is_jiodrive = True if "jiodrive" in link else False
    is_drivefire = True if "drivefire" in link else False
    is_sharerpw = True if "sharer.pw" in link else False
    is_gplinks = True if "Gá´ÊÉªÉ´á´" in link else False
    is_droplink = True if "DÊá´á´ÊÉªÉ´á´" in link else False
    reply_message = ""
    if is_gdtot:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Gá´á´á´á´ LÉªÉ´á´ â¢ <code>{link}</code>", bot, message
            )
            link = gdtot(link)
            deleteMessage(bot, msg)
            LOGGER.info("Gdtot Link Processed")
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_driveapp:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊÉªá´ á´á´á´á´ LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_appdrive:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Aá´á´ÊÉªá´ á´ LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_hubdrive:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Há´Êá´ÊÉªá´ á´ LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = hubdrive_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivehub:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊÉªá´ á´Êá´Ê LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_kolop:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Ká´Êá´á´ LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = kolop_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivebuzz:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊÉªá´ á´Êá´á´¢á´¢ LÉªÉ´á´ â¢ \n<code>{link}</code>",
                bot,
                message,
            )
            link = drivebuzz_dl(link)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_gdflix:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Gá´ê°ÊÉªx LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivesharer:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊÉªá´ á´sÊá´Êá´Ê LÉªÉ´á´ â¢ \n<code>{link}</code>",
                bot,
                message,
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivebit:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊÉªá´ á´ÊÉªá´ LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivelink:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Drivelink LÉªÉ´á´ â¢ \n<code>{link}</code>",
                bot,
                message,
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_katdrive:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Ká´Êá´ÊÉªá´ á´ LÉªÉ´á´ â¢ \n<code>{link}</code>", bot, message
            )
            link = katdrive_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_gadrive:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Já´á´ÊÉªá´ á´ LÉªÉ´á´ â¢ \n<code>{link}</code>",
                bot,
                message,
            )
            link = gadrive_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_jiodrive:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ JÉªá´á´ÊÉªá´ á´ LÉªÉ´á´ â¢ \n<code>{link}</code>",
                bot,
                message,
            )
            link = jiodrive_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivefire:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊÉªá´ á´ê°ÉªÊá´ LÉªÉ´á´ â¢ \n<code>{link}</code>",
                bot,
                message,
            )
            link = drivefire_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_sharerpw:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ SÊá´Êá´Êá´á´¡ LÉªÉ´á´ â¢  \n<code>{link}</code>", bot, message
            )
            link = sharerpw_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_gplinks:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ Gá´ÊÉªÉ´á´ LÉªÉ´á´ â¢  \n<code>{link}</code>", bot, message
            )
            link = gplinks_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_droplink:
        try:
            msg = sendMessage(
                f"PÊá´á´á´ssÉªÉ´É¢ DÊá´á´ÊÉªÉ´á´ LÉªÉ´á´ â¢  \n<code>{link}</code>", bot, message
            )
            link = droplink_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    if reply_message != "":
        Thread(
            target=auto_delete_upload_message, args=(bot, message, reply_message)
        ).start()
        return reply_message
    else:
        if is_gdrive_link(link):
            msg = sendMessage(f"Cá´á´É´á´ÉªÉ´É¢ï¹ <code>{link}</code>", bot, message)
            gd = GoogleDriveHelper()
            result = gd.count(link)
            deleteMessage(bot, msg)
            result += f"\nâ° ð¬ BÊ â¢ {tag}"
            result += f"\nâ° EÊá´á´sá´á´ TÉªá´á´ â¢ {get_readable_time(time() - message.date.timestamp())}\n"
            if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
                reply_to = message.reply_to_message
                if reply_to is not None:
                    try:
                        Thread(
                            target=auto_delete_reply_message, args=(bot, message)
                        ).start()
                    except Exception as error:
                        LOGGER.warning(error)
            reply_message = sendMessage(result, bot, message)
            Thread(
                target=auto_delete_upload_message, args=(bot, message, reply_message)
            ).start()
            if is_gdtot:
                gd.deletefile(link)
            elif is_appdrive:
                gd.deletefile(link)
            elif is_driveapp:
                gd.deletefile(link)
            elif is_hubdrive:
                gd.deletefile(link)
            elif is_drivehub:
                gd.deletefile(link)
            elif is_kolop:
                gd.deletefile(link)
            elif is_drivebuzz:
                gd.deletefile(link)
            elif is_gdflix:
                gd.deletefile(link)
            elif is_drivesharer:
                gd.deletefile(link)
            elif is_drivebit:
                gd.deletefile(link)
            elif is_katdrive:
                gd.deletefile(link)
            elif is_drivefire:
                gd.deletefile(link)
            elif is_gadrive:
                gd.deletefile(link)
            elif is_jiodrive:
                gd.deletefile(link)
            elif is_drivelink:
                gd.deletefile(link)
            elif is_sharerpw:
                gd.deletefile(link)
            elif is_gplinks:
                gd.deletefile(link)
            elif is_droplink:
                gd.deletefile(link)
        else:
            elapsed_time = f"\n\nâ° EÊá´á´sá´á´ TÉªá´á´ â¢ {get_readable_time(time() - message.date.timestamp())}\n"
            reply_message = sendMessage(
                f"Sá´É´á´ Gá´ÊÉªá´ á´/ Gá´á´á´á´/ DÊÉªá´ á´á´á´á´/ Aá´á´ÊÉªá´ á´/ Há´Êá´ÊÉªá´ á´/ DÊÉªá´ á´Êá´Ê/ Ká´Êá´á´/ DÊÉªá´ á´Êá´á´¢á´¢/ Gá´ê°ÊÉªx/ DÊÉªá´ á´sÊá´Êá´Ê/ DÊÉªá´ á´ÊÉªá´/ Drivelink/ Ká´Êá´ÊÉªá´ á´/ Já´á´ÊÉªá´ á´/ DÊÉªá´ á´ê°ÉªÊá´/ SÊá´Êá´Êá´á´¡ ðð¥ð¨ð§ð  ð°ð¢ð­ð¡ ð©ð«ð¨ð©ðð« ðð¨ð¦ð¦ðð§ð ð¨ð« ðð² ð«ðð©ð¥ð²ð¢ð§ð  ð­ð¨ ð­ð¡ð ð¥ð¢ð§ð¤ ðð² ðð¨ð¦ð¦ðð§ð {elapsed_time}",
                bot,
                message,
            )
            Thread(
                target=auto_delete_message, args=(bot, message, reply_message)
            ).start()


@new_thread
def countNode(update, context):
    _count(update.message, context.bot)


count_handler = CommandHandler(
    BotCommands.CountCommand,
    countNode,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
dispatcher.add_handler(count_handler)
