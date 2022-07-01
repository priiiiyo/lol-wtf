from html import escape
from random import SystemRandom
from string import ascii_letters, digits
from threading import Thread
from time import sleep, time

from telegram import InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
    BOT_PM,
    CHANNEL_USERNAME,
    CLONE_LIMIT,
    FSUB,
    FSUB_CHANNEL_ID,
    LINK_LOGS,
    LOGGER,
    MIRROR_LOGS,
    MIRROR_LOGS_CHANNEL_LINK,
    STOP_DUPLICATE,
    Interval,
    dispatcher,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    is_gdrive_link,
    is_gdtot_link,
    new_thread,
    secondsToText,
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
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    auto_delete_reply_message,
    auto_delete_upload_message,
    delete_all_messages,
    deleteMessage,
    sendMarkup,
    sendMessage,
    sendStatusMessage,
    update_all_messages,
)


@new_thread
def _clone(message, bot, multi=0):
    if FSUB:
        try:
            uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            user = bot.get_chat_member(f"{FSUB_CHANNEL_ID}", message.from_user.id)
            LOGGER.error(user.status)
            if user.status not in ("member", "creator", "administrator"):
                buttons = ButtonMaker()
                buttons.buildbutton(
                    "ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ",
                    f"https://t.me/{CHANNEL_USERNAME}",
                )
                reply_markup = InlineKeyboardMarkup(buttons.build_menu(1))
                message = sendMarkup(
                    str(
                        f"<b>Dᴇᴀʀ {uname}️ Yᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ ʏᴇᴛ.</b>\n\nKindly Join @{CHANNEL_USERNAME} To Use Bots. "
                    ),
                    bot,
                    message,
                    reply_markup,
                )
                return
        except BaseException:
            pass
    if BOT_PM and message.chat.type != "private":
        try:
            msg1 = f"Lɪɴᴋ Aᴅᴅᴇᴅ"
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
                "👉🏻 START BOT 👈🏻", f"https://t.me/{bot.get_me().username}?start=start"
            )
            help_msg = f"Dᴇᴀʀ {uname},\nYᴏᴜ ɴᴇᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴜsɪɴɢ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ.  \n\nIᴛs ɴᴇᴇᴅᴇᴅ ᴛᴏ ʙᴏᴛ ᴄᴀɴ sᴇɴᴅ ʏᴏᴜʀ Mɪʀʀᴏʀ/Cʟᴏɴᴇ/Lᴇᴇᴄʜᴇᴅ Fɪʟᴇs ɪɴ BOT PM. \n\nCʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴀɴᴅ Tʀʏ Aɢᴀɪɴ."
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
        if link.isdigit():
            multi = int(link)
            link = ""
        elif message.from_user.username:
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
    LOGGER.info(link)
    source_link = link
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
    is_gplinks = True if "Gᴘʟɪɴᴋ" in link else False
    is_droplink = True if "Dʀᴏᴘʟɪɴᴋ" in link else False
    reply_message = ""
    if is_gdtot:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Gᴅᴛᴏᴛ Lɪɴᴋ ⇢ <code>{link}</code>", bot, message
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
                f"Pʀᴏᴄᴇssɪɴɢ Dʀɪᴠᴇᴀᴘᴘ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_appdrive:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Aᴘᴘʀɪᴠᴇ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_hubdrive:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Hᴜʙᴅʀɪᴠᴇ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = hubdrive_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivehub:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Dʀɪᴠᴇʜᴜʙ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_kolop:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Kᴏʟᴏᴘ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = kolop_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivebuzz:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Dʀɪᴠᴇʙᴜᴢᴢ Lɪɴᴋ ⇢ \n<code>{link}</code>",
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
                f"Pʀᴏᴄᴇssɪɴɢ Gᴏꜰʟɪx Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivesharer:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Dʀɪᴠᴇsʜᴀʀᴇʀ Lɪɴᴋ ⇢ \n<code>{link}</code>",
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
                f"Pʀᴏᴄᴇssɪɴɢ Dʀɪᴠᴇʙɪᴛ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_drivelink:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Drivelink Lɪɴᴋ ⇢ \n<code>{link}</code>",
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
                f"Pʀᴏᴄᴇssɪɴɢ Kᴀʀᴅʀɪᴠᴇ Lɪɴᴋ ⇢ \n<code>{link}</code>", bot, message
            )
            link = katdrive_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_gadrive:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Jᴀᴅʀɪᴠᴇ Lɪɴᴋ ⇢ \n<code>{link}</code>",
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
                f"Pʀᴏᴄᴇssɪɴɢ Jɪᴏᴅʀɪᴠᴇ Lɪɴᴋ ⇢ \n<code>{link}</code>",
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
                f"Pʀᴏᴄᴇssɪɴɢ Dʀɪᴠᴇꜰɪʀᴇ Lɪɴᴋ ⇢ \n<code>{link}</code>",
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
                f"Pʀᴏᴄᴇssɪɴɢ Sʜᴀʀᴇʀᴘᴡ Lɪɴᴋ ⇢  \n<code>{link}</code>", bot, message
            )
            link = sharerpw_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_gplinks:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Gᴘʟɪɴᴋ Lɪɴᴋ ⇢  \n<code>{link}</code>", bot, message
            )
            link = gplinks_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)
    elif is_droplink:
        try:
            msg = sendMessage(
                f"Pʀᴏᴄᴇssɪɴɢ Dʀᴏᴘʟɪɴᴋ Lɪɴᴋ ⇢  \n<code>{link}</code>", bot, message
            )
            link = droplink_dl(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            reply_message = sendMessage(str(e), bot, message)

    if reply_message != "":
        Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
        return reply_message
    else:
        if is_gdrive_link(link):
            gd = GoogleDriveHelper()
            res, size, name, files = gd.helper(link)
            if res != "":
                res += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}\n"
                reply_message = sendMessage(res, bot, message)
                Thread(
                    target=auto_delete_upload_message,
                    args=(bot, message, reply_message),
                ).start()
                return reply_message
            if STOP_DUPLICATE:
                LOGGER.info("Checking File/Folder if already in Drive...")
                smsg, button = gd.drive_list(name, True, True)
                if smsg:
                    msg3 = "📂 Fɪʟᴇ/Fᴏʟᴅᴇʀ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ Dʀɪᴠᴇ.\nHᴇʀᴇ ᴀʀᴇ ᴛʜᴇ sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs﹕"
                    msg3 += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}\n"
                    reply_message = sendMarkup(msg3, bot, message, button)
                    Thread(
                        target=auto_delete_upload_message,
                        args=(bot, message, reply_message),
                    ).start()
                    return reply_message
            if CLONE_LIMIT is not None:
                LOGGER.info("Checking File/Folder Size...")
                if size > CLONE_LIMIT * 1024**3:
                    msg2 = f"Fᴀɪʟᴇᴅ, Cʟᴏɴᴇ ʟɪᴍɪᴛ ɪs {CLONE_LIMIT}GB.\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}."
                    msg2 += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}\n"
                    reply_message = sendMessage(msg2, bot, message)
                    Thread(
                        target=auto_delete_upload_message,
                        args=(bot, message, reply_message),
                    ).start()
                    return reply_message
            if multi > 1:
                sleep(4)
                nextmsg = type(
                    "nextmsg",
                    (object,),
                    {
                        "chat_id": message.chat_id,
                        "message_id": message.reply_to_message.message_id + 1,
                    },
                )
                nextmsg = sendMessage(args[0], bot, nextmsg)
                nextmsg.from_user.id = message.from_user.id
                multi -= 1
                sleep(4)
                Thread(target=_clone, args=(nextmsg, bot, multi)).start()
            if files <= 20:
                msg = sendMessage(
                    f"⚙️ Cʟᴏɴɪɴɢ Yᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ Iɴᴛᴏ ᴍʏ Dʀɪᴠᴇ﹗\n Yᴏᴜʀ Lɪɴᴋ﹕ <code>{link}</code>",
                    bot,
                    message,
                )
                result, button = gd.clone(link, source_link)
                deleteMessage(bot, msg)
            else:
                drive = GoogleDriveHelper(name)
                gid = "".join(SystemRandom().choices(ascii_letters + digits, k=12))
                clone_status = CloneStatus(drive, size, message, gid)
                with download_dict_lock:
                    download_dict[message.message_id] = clone_status
                sendStatusMessage(message, bot)
                result, button = drive.clone(link, source_link)
                with download_dict_lock:
                    del download_dict[message.message_id]
                    count = len(download_dict)
                try:
                    if count == 0:
                        Interval[0].cancel()
                        del Interval[0]
                        delete_all_messages()
                    else:
                        update_all_messages()
                except IndexError:
                    pass
            result += f"\n╰ 📬 Bʏ ⇢ {tag}"
            result += f"\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}\n"
            cbutton = InlineKeyboardMarkup(button.build_menu(2))
            if cbutton in ["cancelled", ""]:
                reply_message = sendMessage(f"{tag} {result}", bot, message)
            else:
                if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
                    reply_to = message.reply_to_message
                    if reply_to is not None:
                        try:
                            Thread(
                                target=auto_delete_reply_message, args=(bot, message)
                            ).start()
                        except Exception as error:
                            LOGGER.warning(error)
                    if message.chat.type == "private":
                        warnmsg = ""
                    else:
                        autodel = secondsToText()
                        warnmsg = f"\nTʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ Aᴜᴛᴏ Dᴇʟᴇᴛᴇ ɪɴ {autodel}\n\n"
                else:
                    warnmsg = ""
                if BOT_PM and message.chat.type != "private":
                    pmwarn_clone = f"\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ BOT PM."
                    try:
                        replymsg = bot.sendMessage(
                            chat_id=message.from_user.id,
                            text=result,
                            reply_markup=InlineKeyboardMarkup(button.build_menu(2)),
                            parse_mode=ParseMode.HTML,
                        )
                        button.sbutton(
                            "Vɪᴇᴡ Fɪʟᴇ ɪɴ PM",
                            f"botpmfilebutton {message.from_user.id} {replymsg.message_id}",
                        )
                    except Exception as e:
                        LOGGER.warning(f"Unable to send file to PM: {str(e)}")
                elif message.chat.type == "private":
                    pmwarn_clone = ""
                else:
                    pmwarn_clone = ""
                if MIRROR_LOGS and message.chat.type != "private":
                    for i in MIRROR_LOGS:
                        try:
                            replymsg = bot.sendMessage(
                                chat_id=i,
                                text=result,
                                reply_markup=InlineKeyboardMarkup(button.build_menu(2)),
                                parse_mode=ParseMode.HTML,
                            )
                            if message.chat_id != i:
                                try:
                                    log_channel = MIRROR_LOGS_CHANNEL_LINK
                                    clone_chat_id = str(MIRROR_LOGS)[5:][:-1]
                                    clone_file = f"https://t.me/c/{clone_chat_id}/{replymsg.message_id}"
                                    logwarn_clone = f'\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ <a href="{log_channel}">Mɪʀʀᴏʀ/Cʟᴏɴᴇ Lᴏɢs Cʜᴀɴɴᴇʟ</a>.'
                                    logwarn_clone += f'\n Jᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴜsɪɴɢ ᴛʜᴇ ᴀʙᴏᴠᴇ ʟɪɴᴋ ᴛᴏ sᴇᴇ ʏᴏᴜʀ <a href="{clone_file}">Cʟᴏɴᴇᴅ Fɪʟᴇs</a>.'
                                except Exception as ex:
                                    LOGGER.warning(
                                        f"Error in logwarn_clone string: {str(ex)}"
                                    )
                                    logwarn_clone = "\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ Mɪʀʀᴏʀ/Cʟᴏɴᴇ Lᴏɢs Cʜᴀɴɴᴇʟ</a>."
                        except Exception as e:
                            LOGGER.warning(f"Issue with Mirror Logs : {str(e)}")
                elif message.chat.type == "private":
                    logwarn_clone = ""
                else:
                    logwarn_clone = ""
                if LINK_LOGS and message.chat.type != "private" and link != "":
                    slmsg = f"\n╭ 📂 Fɪʟᴇɴᴀᴍᴇ ⇢ <code>{escape(name)}</code>"
                    slmsg += f"\n├ 🕹️ Sɪᴢᴇ ⇢ {get_readable_file_size(size)}"
                    if message.from_user.username:
                        uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.username}</a>'
                    else:
                        uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
                    slmsg += f"\n╰ 🪧 Aᴅᴅᴇᴅ Bʏ ⇢ {uname} \n\n"
                    try:
                        sourcelink = f"<code>{source_link}</code>"
                        for link_log in LINK_LOGS:
                            bot.sendMessage(
                                chat_id=link_log,
                                text=slmsg + sourcelink,
                                parse_mode=ParseMode.HTML,
                            )
                    except IndexError:
                        pass
                reply_message = sendMarkup(
                    result + pmwarn_clone + logwarn_clone + warnmsg,
                    bot,
                    message,
                    InlineKeyboardMarkup(button.build_menu(2)),
                )
            Thread(
                target=auto_delete_upload_message,
                args=(bot, message, reply_message),
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
            LOGGER.info(f"Cloning Done: {name}")
        else:
            elapsed_time = f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}\n"
            reply_message = sendMessage(
                f"Sᴇɴᴅ Gᴅʀɪᴠᴇ/ Gᴅᴛᴏᴛ/ Dʀɪᴠᴇᴀᴘᴘ/ Aᴘᴘʀɪᴠᴇ/ Hᴜʙᴅʀɪᴠᴇ/ Dʀɪᴠᴇʜᴜʙ/ Kᴏʟᴏᴘ/ Dʀɪᴠᴇʙᴜᴢᴢ/ Gᴏꜰʟɪx/ Dʀɪᴠᴇsʜᴀʀᴇʀ/ Dʀɪᴠᴇʙɪᴛ/ Drivelink/ Kᴀʀᴅʀɪᴠᴇ/ Jᴀᴅʀɪᴠᴇ/ Jɪᴏᴅʀɪᴠᴇ/ Dʀɪᴠᴇꜰɪʀᴇ/ Sʜᴀʀᴇʀᴘᴡ 𝐚𝐥𝐨𝐧𝐠 𝐰𝐢𝐭𝐡 𝐩𝐫𝐨𝐩𝐞𝐫 𝐂𝐨𝐦𝐦𝐚𝐧𝐝 𝐨𝐫 𝐛𝐲 𝐫𝐞𝐩𝐥𝐲𝐢𝐧𝐠 𝐭𝐨 𝐭𝐡𝐞 𝐥𝐢𝐧𝐤 𝐛𝐲 𝐂𝐨𝐦𝐦𝐚𝐧𝐝 {elapsed_time}",
                bot,
                message,
            )
            Thread(
                target=auto_delete_message, args=(bot, message, reply_message)
            ).start()


def bot_pm_button_handle(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split(" ")
    if user_id != int(data[1]):
        return query.answer(
            text="Since you didnt perform this task, you cant see it in your BOT PM",
            show_alert=True,
        )
    else:
        bot_d = context.bot.get_me()
        b_uname = bot_d.username
        boturl = f"https://t.me/{b_uname}?start={int(data[2])}"
        return query.answer(url=boturl)


botpmbutton = CallbackQueryHandler(
    bot_pm_button_handle, pattern="botpmfilebutton", run_async=True
)
dispatcher.add_handler(botpmbutton)


@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)


clone_handler = CommandHandler(
    BotCommands.CloneCommand,
    cloneNode,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
dispatcher.add_handler(clone_handler)
