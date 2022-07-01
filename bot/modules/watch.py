from re import split as re_split
from threading import Thread
from time import sleep

from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    BOT_PM,
    CHANNEL_USERNAME,
    DOWNLOAD_DIR,
    FSUB,
    FSUB_CHANNEL_ID,
    LEECH_ENABLED,
    LOGGER,
    dispatcher,
)
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_url
from bot.helper.mirror_utils.download_utils.youtube_dl_download_helper import (
    YoutubeDLHelper,
)
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    auto_delete_upload_message,
    editMessage,
    sendMarkup,
    sendMessage,
)

from .mirror import MirrorListener

listener_dict = {}


def _watch(bot, message, isZip=False, isLeech=False, multi=0):
    if FSUB:
        try:
            user = bot.get_chat_member(f"{FSUB_CHANNEL_ID}", message.from_user.id)
            LOGGER.info(user.status)
            if user.status not in ("member", "creator", "administrator", "supergroup"):
                if message.from_user.username:
                    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.username}</a>'
                else:
                    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
                buttons = button_build.ButtonMaker()
                chat_u = CHANNEL_USERNAME.replace("@", "")
                buttons.buildbutton("👉🏻 CHANNEL LINK 👈🏻", f"https://t.me/{chat_u}")
                help_msg = f"Dᴇᴀʀ {uname},\nYᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴍʏ Cʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ Bᴏᴛ \n\nCʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴇʟᴏᴡ Bᴜᴛᴛᴏɴ ᴛᴏ ᴊᴏɪɴ ᴍʏ Cʜᴀɴɴᴇʟ."
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
            buttons = button_build.ButtonMaker()
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
    mssg = message.text
    user_id = message.from_user.id
    msg_id = message.message_id
    link = mssg.split()
    if len(link) > 1:
        link = link[1].strip()
        if link.isdigit():
            multi = int(link)
            link = ""
        elif link.startswith(("|", "pswd:", "args:")):
            link = ""
    else:
        link = ""

    name = mssg.split("|", maxsplit=1)
    if len(name) > 1:
        if "args: " in name[0] or "pswd: " in name[0]:
            name = ""
        else:
            name = name[1]
        if name != "":
            name = re_split("pswd:|args:", name)[0]
            name = name.strip()
    else:
        name = ""

    pswd = mssg.split(" pswd: ")
    if len(pswd) > 1:
        pswd = pswd[1]
        pswd = pswd.split(" args: ")[0]
    else:
        pswd = None

    args = mssg.split(" args: ")
    if len(args) > 1:
        args = args[1]
    else:
        args = None

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    reply_to = message.reply_to_message
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text.strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

    if not is_url(link):
        help_msg = "<b>Send link along with command line:</b>"
        help_msg += "\n<code>/command</code> {link} |newname pswd: mypassword [zip] args: x:y|x1:y1"
        help_msg += "\n\n<b>By replying to link:</b>"
        help_msg += (
            "\n<code>/command</code> |newname pswd: mypassword [zip] args: x:y|x1:y1"
        )
        help_msg += "\n\n<b>Args Example:</b> args: playliststart:^10|match_filter:season_number=18|matchtitle:S1"
        help_msg += "\n\n<b>NOTE:</b> Add `^` before integer, some values must be integer and some string."
        help_msg += " Like playlist_items:10 works with string so no need to add `^` before the number"
        help_msg += " but playlistend works only with integer so you must add `^` before the number like example above."
        help_msg += "\n\nCheck all arguments from this <a href='https://github.com/yt-dlp/yt-dlp/blob/a3125791c7a5cdf2c8c025b99788bf686edd1a8a/yt_dlp/YoutubeDL.py#L194'>FILE</a>."
        reply_message = sendMessage(help_msg, bot, message)
        Thread(
            target=auto_delete_upload_message, args=(bot, message, reply_message)
        ).start()
        return reply_message
    LOGGER.info(link)
    listener = MirrorListener(
        bot, message, isZip, isLeech=isLeech, pswd=pswd, tag=tag, link=link
    )
    buttons = button_build.ButtonMaker()
    best_video = "bv*+ba/b"
    best_audio = "ba/b"
    ydl = YoutubeDLHelper(listener)
    try:
        result = ydl.extractMetaData(link, name, args, True)
    except Exception as e:
        msg = str(e).replace("<", " ").replace(">", " ")
        reply_message = sendMessage(tag + " " + msg, bot, message)
        Thread(
            target=auto_delete_upload_message, args=(bot, message, reply_message)
        ).start()
        return reply_message
    if "entries" in result:
        for i in ["144", "240", "360", "480", "720", "1080", "1440", "2160"]:
            video_format = f"bv*[height<={i}][ext=mp4]"
            buttons.sbutton(f"{i}-mp4", f"qu {msg_id} {video_format} t")
            video_format = f"bv*[height<={i}][ext=webm]"
            buttons.sbutton(f"{i}-webm", f"qu {msg_id} {video_format} t")
        buttons.sbutton("Aᴜᴅɪᴏs", f"qu {msg_id} audio t")
        buttons.sbutton("Bᴇsᴛ Vɪᴅᴇᴏs", f"qu {msg_id} {best_video} t")
        buttons.sbutton("Bᴇsᴛ Aᴜᴅɪᴏs", f"qu {msg_id} {best_audio} t")
        buttons.sbutton("Cᴀɴᴄᴇʟ", f"qu {msg_id} cancel")
        YTBUTTONS = InlineKeyboardMarkup(buttons.build_menu(3))
        listener_dict[msg_id] = [listener, user_id, link, name, YTBUTTONS, args]
        bmsg = sendMarkup(
            "Cʜᴏᴏsᴇ Pʟᴀʏʟɪsᴛ Vɪᴅᴇᴏ Qᴜᴀʟɪᴛʏ ⇢ \nTʜɪs Tᴀsᴋ ᴡɪʟʟ ᴀᴜᴛᴏ ᴄᴀɴᴄᴇʟ ɪɴ 2 ᴍɪɴᴜᴛᴇs",
            bot,
            message,
            YTBUTTONS,
        )
    else:
        formats = result.get("formats")
        formats_dict = {}
        if formats is not None:
            for frmt in formats:
                if not frmt.get("tbr") or not frmt.get("height"):
                    continue

                if frmt.get("fps"):
                    quality = f"{frmt['height']}p{frmt['fps']}-{frmt['ext']}"
                else:
                    quality = f"{frmt['height']}p-{frmt['ext']}"

                if frmt.get("filesize"):
                    size = frmt["filesize"]
                elif frmt.get("filesize_approx"):
                    size = frmt["filesize_approx"]
                else:
                    size = 0

                if quality in list(formats_dict.keys()):
                    formats_dict[quality][frmt["tbr"]] = size
                else:
                    subformat = {}
                    subformat[frmt["tbr"]] = size
                    formats_dict[quality] = subformat

            for _format in formats_dict:
                if len(formats_dict[_format]) == 1:
                    qual_fps_ext = re_split(r"p|-", _format, maxsplit=2)
                    height = qual_fps_ext[0]
                    fps = qual_fps_ext[1]
                    ext = qual_fps_ext[2]
                    if fps != "":
                        video_format = f"bv*[height={height}][fps={fps}][ext={ext}]"
                    else:
                        video_format = f"bv*[height={height}][ext={ext}]"
                    size = list(formats_dict[_format].values())[0]
                    buttonName = f"{_format} ({get_readable_file_size(size)})"
                    buttons.sbutton(str(buttonName), f"qu {msg_id} {video_format}")
                else:
                    buttons.sbutton(str(_format), f"qu {msg_id} dict {_format}")
        buttons.sbutton("Aᴜᴅɪᴏ", f"qu {msg_id} audio")
        buttons.sbutton("Bᴇsᴛ Vɪᴅᴇᴏ", f"qu {msg_id} {best_video}")
        buttons.sbutton("Bᴇsᴛ Aᴜᴅɪᴏ", f"qu {msg_id} {best_audio}")
        buttons.sbutton("Cᴀɴᴄᴇʟ", f"qu {msg_id} cancel")
        YTBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
        listener_dict[msg_id] = [
            listener,
            user_id,
            link,
            name,
            YTBUTTONS,
            args,
            formats_dict,
        ]
        bmsg = sendMarkup(
            "Cʜᴏᴏsᴇ Vɪᴅᴇᴏ Qᴜᴀʟɪᴛʏ ⇢ \nTʜɪs Tᴀsᴋ ᴡɪʟʟ ᴀᴜᴛᴏ ᴄᴀɴᴄᴇʟ ɪɴ 2 ᴍɪɴᴜᴛᴇs",
            bot,
            message,
            YTBUTTONS,
        )
    Thread(target=_auto_cancel, args=(bot, message, bmsg, msg_id)).start()
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
        nextmsg = sendMessage(mssg.split(" ")[0], bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        multi -= 1
        sleep(4)
        Thread(target=_watch, args=(bot, nextmsg, isZip, isLeech, multi)).start()


def _qual_subbuttons(task_id, qual, msg):
    buttons = button_build.ButtonMaker()
    task_info = listener_dict[task_id]
    formats_dict = task_info[6]
    qual_fps_ext = re_split(r"p|-", qual, maxsplit=2)
    height = qual_fps_ext[0]
    fps = qual_fps_ext[1]
    ext = qual_fps_ext[2]
    tbrs = list(formats_dict[qual])
    tbrs.sort(reverse=True)
    for index, br in enumerate(tbrs):
        if index == 0:
            tbr = f">{br}"
        else:
            sbr = index - 1
            tbr = f"<{tbrs[sbr]}"
        if fps != "":
            video_format = f"bv*[height={height}][fps={fps}][ext={ext}][tbr{tbr}]"
        else:
            video_format = f"bv*[height={height}][ext={ext}][tbr{tbr}]"
        size = formats_dict[qual][br]
        buttonName = f"{br}K ({get_readable_file_size(size)})"
        buttons.sbutton(str(buttonName), f"qu {task_id} {video_format}")
    buttons.sbutton("Bᴀᴄᴋ", f"qu {task_id} back")
    buttons.sbutton("Cᴀɴᴄᴇʟ", f"qu {task_id} cancel")
    SUBBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
    editMessage(f"Cʜᴏᴏsᴇ Vɪᴅᴇᴏ Bɪᴛʀᴀᴛᴇ ꜰᴏʀ <b>{qual}</b>: ", msg, SUBBUTTONS)


def _audio_subbuttons(task_id, msg, playlist=False):
    buttons = button_build.ButtonMaker()
    audio_qualities = [64, 128, 320]
    for q in audio_qualities:
        if playlist:
            i = "s"
            audio_format = f"ba/b-{q} t"
        else:
            i = ""
            audio_format = f"ba/b-{q}"
        buttons.sbutton(f"{q}K-mp3", f"qu {task_id} {audio_format}")
    buttons.sbutton("Bᴀᴄᴋ", f"qu {task_id} back")
    buttons.sbutton("Cᴀɴᴄᴇʟ", f"qu {task_id} cancel")
    SUBBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
    editMessage(f"Cʜᴏᴏsᴇ Aᴜᴅɪᴏ{i} Bɪᴛʀᴀᴛᴇ: ", msg, SUBBUTTONS)


def select_format(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    msg = query.message
    data = data.split(" ")
    task_id = int(data[1])
    try:
        task_info = listener_dict[task_id]
    except BaseException:
        return editMessage("This is an old task", msg)
    uid = task_info[1]
    if user_id != uid and not CustomFilters._owner_query(user_id):
        return query.answer(text="This task is not for you!", show_alert=True)
    elif data[2] == "dict":
        query.answer()
        qual = data[3]
        _qual_subbuttons(task_id, qual, msg)
        return
    elif data[2] == "back":
        query.answer()
        return editMessage("Cʜᴏᴏsᴇ Vɪᴅᴇᴏ Qᴜᴀʟɪᴛʏ ⇢ ", msg, task_info[4])
    elif data[2] == "audio":
        query.answer()
        playlist = len(data) == 4
        _audio_subbuttons(task_id, msg, playlist)
        return
    elif data[2] == "cancel":
        query.answer()
        reply_message = editMessage("Tᴀsᴋ ʜᴀs ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ..", msg)
        Thread(
            target=auto_delete_message,
            args=(context.bot, query.message, reply_message),
        ).start()
        return reply_message
    else:
        query.answer()
        listener = task_info[0]
        link = task_info[2]
        name = task_info[3]
        args = task_info[5]
        qual = data[2]
        # To not exceed telegram button bytes limits. Temp solution.
        if qual.startswith("bv*["):
            height = re_split(r"\[|\]", qual, maxsplit=2)[1]
            qual = qual + f"+ba/b[{height}]"
        playlist = len(data) == 4
        ydl = YoutubeDLHelper(listener)
        Thread(
            target=ydl.add_download,
            args=(link, f"{DOWNLOAD_DIR}{task_id}", name, qual, playlist, args),
        ).start()
        query.message.delete()
    del listener_dict[task_id]


def _auto_cancel(bot, message, msg, msg_id):
    sleep(120)
    try:
        del listener_dict[msg_id]
        reply_message = editMessage("Tɪᴍᴇᴅ ᴏᴜᴛ﹗ Tᴀsᴋ ʜᴀs ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.", msg)
        Thread(
            target=auto_delete_upload_message,
            args=(bot, message, reply_message),
        ).start()
    except Exception:
        pass


def watch(update, context):
    _watch(context.bot, update.message)


def watchZip(update, context):
    _watch(context.bot, update.message, True)


def leechWatch(update, context):
    _watch(context.bot, update.message, isLeech=True)


def leechWatchZip(update, context):
    _watch(context.bot, update.message, True, True)


watch_handler = CommandHandler(
    BotCommands.WatchCommand,
    watch,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
zip_watch_handler = CommandHandler(
    BotCommands.ZipWatchCommand,
    watchZip,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
dispatcher.add_handler(watch_handler)
dispatcher.add_handler(zip_watch_handler)

if LEECH_ENABLED:
    leech_watch_handler = CommandHandler(
        BotCommands.LeechWatchCommand,
        leechWatch,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    leech_zip_watch_handler = CommandHandler(
        BotCommands.LeechZipWatchCommand,
        leechWatchZip,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    dispatcher.add_handler(leech_watch_handler)
    dispatcher.add_handler(leech_zip_watch_handler)

quality_handler = CallbackQueryHandler(select_format, pattern="qu", run_async=True)
dispatcher.add_handler(quality_handler)
