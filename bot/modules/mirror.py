from base64 import b64encode
from datetime import datetime
from html import escape
from os import listdir
from os import path as ospath
from os import remove as osremove
from os import walk
from pathlib import PurePath
from re import match as re_match
from re import search as re_search
from re import split as re_split
from shutil import rmtree
from subprocess import run as srun
from threading import Thread
from time import sleep, time
from urllib.parse import quote

from pytz import timezone
from requests import utils as rutils
from telegram import InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
    BOT_PM,
    BUTTON_FIVE_NAME,
    BUTTON_FIVE_URL,
    BUTTON_FOUR_NAME,
    BUTTON_FOUR_URL,
    BUTTON_SIX_NAME,
    BUTTON_SIX_URL,
    CHANNEL_USERNAME,
    DB_URI,
    DOWNLOAD_DIR,
    FSUB,
    FSUB_CHANNEL_ID,
    INCOMPLETE_TASK_NOTIFIER,
    INDEX_URL,
    LEECH_ENABLED,
    LEECH_LOG,
    LEECH_LOG_CHANNEL_LINK,
    LINK_LOGS,
    LOGGER,
    MEGA_KEY,
    MIRROR_LOGS,
    MIRROR_LOGS_CHANNEL_LINK,
    QB_SEED,
    SOURCE_LINK,
    TG_SPLIT_SIZE,
    TIMEZONE,
    VIEW_LINK,
    Interval,
    aria2,
    bot,
    dispatcher,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_content_type,
    get_readable_time,
    is_gdrive_link,
    is_gdtot_link,
    is_magnet,
    is_mega_link,
    is_url,
    secondsToText,
)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import (
    DirectDownloadLinkException,
    NotSupportedExtractionArchive,
)
from bot.helper.ext_utils.fs_utils import clean_download, get_base_name, get_path_size
from bot.helper.ext_utils.fs_utils import split_file as fs_split
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.mega_downloader import MegaDownloader
from bot.helper.mirror_utils.download_utils.qbit_downloader import QbDownloader
from bot.helper.mirror_utils.download_utils.telegram_downloader import (
    TelegramDownloadHelper,
)
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.tg_upload_status import TgUploadStatus
from bot.helper.mirror_utils.status_utils.upload_status import UploadStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    auto_delete_reply_message,
    auto_delete_upload_message,
    delete_all_messages,
    sendMarkup,
    sendMessage,
    update_all_messages,
)


class MirrorListener:
    def __init__(
        self,
        bot,
        message,
        isZip=False,
        extract=False,
        isQbit=False,
        isLeech=False,
        pswd=None,
        tag=None,
        link="",
    ):
        self.bot = bot
        self.message = message
        self.uid = self.message.message_id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.pswd = pswd
        self.tag = tag
        self.isPrivate = self.message.chat.type in ["private", "group"]
        self.user_id = self.message.from_user.id
        self.link = link

    def clean(self):
        try:
            aria2.purge()
            Interval[0].cancel()
            del Interval[0]
            delete_all_messages()
        except IndexError:
            pass

    def onDownloadStart(self):
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().add_incomplete_task(
                self.message.chat.id, self.message.link, self.tag
            )

    def onDownloadComplete(self):
        with download_dict_lock:
            LOGGER.info(f"Download completed: {download_dict[self.uid].name()}")
            download = download_dict[self.uid]
            name = str(download.name()).replace("/", "")
            gid = download.gid()
            size = download.size_raw()
            if (
                name == "None"
                or self.isQbit
                or not ospath.exists(f"{DOWNLOAD_DIR}{self.uid}/{name}")
            ):
                name = listdir(f"{DOWNLOAD_DIR}{self.uid}")[-1]
            m_path = f"{DOWNLOAD_DIR}{self.uid}/{name}"
        if self.isZip:
            try:
                with download_dict_lock:
                    download_dict[self.uid] = ZipStatus(
                        name, m_path, size, self.message
                    )
                path = f"{m_path}.zip"
                LOGGER.info(f"Zip: orig_path: {m_path}, zip_path: {path}")
                if self.pswd is not None:
                    if self.isLeech and int(size) > TG_SPLIT_SIZE:
                        srun(
                            [
                                "7z",
                                f"-v{TG_SPLIT_SIZE}b",
                                "a",
                                "-mx=0",
                                f"-p{self.pswd}",
                                path,
                                m_path,
                            ]
                        )
                    else:
                        srun(["7z", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
                elif self.isLeech and int(size) > TG_SPLIT_SIZE:
                    srun(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", path, m_path])
                else:
                    srun(["7z", "a", "-mx=0", path, m_path])
            except FileNotFoundError:
                LOGGER.info("File to archive not found!")
                return self.onUploadError("Iɴᴛᴇʀɴᴀʟ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!")
            if not self.isQbit or not QB_SEED or self.isLeech:
                try:
                    rmtree(m_path)
                except Exception:
                    osremove(m_path)
        elif self.extract:
            try:
                if ospath.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(
                        name, m_path, size, self.message
                    )
                if ospath.isdir(m_path):
                    for dirpath, subdir, files in walk(m_path, topdown=False):
                        for file_ in files:
                            if (
                                file_.endswith((".zip", ".7z"))
                                or re_search(
                                    r"\.part0*1\.rar$|\.7z\.0*1$|\.zip\.0*1$", file_
                                )
                                or (
                                    file_.endswith(".rar")
                                    and not re_search(r"\.part\d+\.rar$", file_)
                                )
                            ):
                                m_path = ospath.join(dirpath, file_)
                                if self.pswd is not None:
                                    result = srun(
                                        [
                                            "7z",
                                            "x",
                                            f"-p{self.pswd}",
                                            m_path,
                                            f"-o{dirpath}",
                                            "-aot",
                                        ]
                                    )
                                else:
                                    result = srun(
                                        ["7z", "x", m_path, f"-o{dirpath}", "-aot"]
                                    )
                                if result.returncode != 0:
                                    LOGGER.error("Unable to extract archive!")
                        for file_ in files:
                            if file_.endswith((".rar", ".zip", ".7z")) or re_search(
                                r"\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$", file_
                            ):
                                del_path = ospath.join(dirpath, file_)
                                osremove(del_path)
                    path = f"{DOWNLOAD_DIR}{self.uid}/{name}"
                else:
                    if self.pswd is not None:
                        result = srun(["bash", "pextract", m_path, self.pswd])
                    else:
                        result = srun(["bash", "extract", m_path])
                    if result.returncode == 0:
                        LOGGER.info(f"Extracted Path: {path}")
                        osremove(m_path)
                    else:
                        LOGGER.error("Unable to extract archive! Uploading anyway")
                        path = f"{DOWNLOAD_DIR}{self.uid}/{name}"
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                path = f"{DOWNLOAD_DIR}{self.uid}/{name}"
        else:
            path = f"{DOWNLOAD_DIR}{self.uid}/{name}"
        up_name = PurePath(path).name
        up_path = f"{DOWNLOAD_DIR}{self.uid}/{up_name}"
        if self.isLeech and not self.isZip:
            checked = False
            for dirpath, subdir, files in walk(
                f"{DOWNLOAD_DIR}{self.uid}", topdown=False
            ):
                for file_ in files:
                    f_path = ospath.join(dirpath, file_)
                    f_size = ospath.getsize(f_path)
                    if int(f_size) > TG_SPLIT_SIZE:
                        if not checked:
                            checked = True
                            with download_dict_lock:
                                download_dict[self.uid] = SplitStatus(
                                    up_name, up_path, size, self.message
                                )
                            LOGGER.info(f"Splitting: {up_name}")
                        fs_split(f_path, f_size, file_, dirpath, TG_SPLIT_SIZE)
                        osremove(f_path)
        if self.isLeech:
            size = get_path_size(f"{DOWNLOAD_DIR}{self.uid}")
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, self)
            tg_upload_status = TgUploadStatus(tg, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            update_all_messages()
            tg.upload()
        else:
            size = get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, self)
            upload_status = UploadStatus(drive, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = upload_status
            update_all_messages()
            drive.upload(up_name)

    def onDownloadError(self, error):
        reply_to = self.message.reply_to_message
        if reply_to is not None:
            try:
                Thread(
                    target=auto_delete_reply_message, args=(self.bot, self.message)
                ).start()
            except Exception:
                pass
        error = error.replace("<", " ").replace(">", " ")
        clean_download(f"{DOWNLOAD_DIR}{self.uid}")
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        if self.message.from_user.username:
            self.tag = f"@{self.message.from_user.username}"
        else:
            self.tag = f'<a href="tg://user?id={self.user_id}">{self.message.from_user.first_name}</a>'
        msg = f"{self.tag} Yᴏᴜʀ Dᴏᴡɴʟᴏᴀᴅ ʜᴀs ʙᴇᴇɴ sᴛᴏᴘᴘᴇᴅ ᴅᴜᴇ ᴛᴏ ⇢ \n{error}"
        msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.message.date.timestamp())}\n"
        reply_message = sendMessage(msg, self.bot, self.message)
        Thread(
            target=auto_delete_upload_message, args=(bot, self.message, reply_message)
        ).start()
        if count == 0:
            self.clean()
        else:
            update_all_messages()
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)

    def onUploadComplete(self, link: str, size, files, folders, typ, name: str):
        kie = datetime.now(timezone(f"{TIMEZONE}"))
        jam = kie.strftime("\nDᴀᴛᴇ : %d/%m/%Y \t\t Tɪᴍᴇ: %I:%M:%S %P")
        if self.message.from_user.username:
            uname = f'<a href="tg://user?id={self.user_id}">{self.message.from_user.username}</a>'
        else:
            uname = f'<a href="tg://user?id={self.user_id}">{self.message.from_user.first_name}</a>'
        buttons = ButtonMaker()
        if LINK_LOGS and self.message.chat.type != "private" and self.link != "":
            slmsg = f"\n╭ 📂 Fɪʟᴇɴᴀᴍᴇ ⇢ <code>{escape(name)}</code>"
            slmsg += f"\n├ 🕹️ Sɪᴢᴇ ⇢ {size}"
            slmsg += f"\n╰ 🪧 Aᴅᴅᴇᴅ Bʏ ⇢ {uname} \n\n"
            try:
                slmsg += f"<code>{self.link}</code>"
                for link_log in LINK_LOGS:
                    bot.sendMessage(
                        chat_id=link_log,
                        text=slmsg,
                        parse_mode=ParseMode.HTML,
                    )
            except IndexError:
                pass
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)
        if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
            reply_to = self.message.reply_to_message
            if reply_to is not None:
                try:
                    Thread(
                        target=auto_delete_reply_message, args=(self.bot, self.message)
                    ).start()
                except Exception as error:
                    LOGGER.warning(error)
            if self.message.chat.type == "private":
                warnmsg = ""
            else:
                autodel = secondsToText()
                warnmsg = f"\nTʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ Aᴜᴛᴏ Dᴇʟᴇᴛᴇ ɪɴ {autodel}\n\n"
        else:
            warnmsg = ""
        if self.isLeech:
            if SOURCE_LINK is True and self.link != "":
                try:
                    source_link = f"{self.link}"
                    if is_magnet(source_link):
                        source_link += f"<br><br>💘 Sʜᴀʀᴇ Mᴀɢɴᴇᴛ Tᴏ <a href='http://t.me/share/url?url={quote(self.link)}'>Tᴇʟᴇɢʀᴀᴍ</a><br>"
                        telegraph_link = telegraph.create_page(
                            title="Dipesh Mɪʀʀᴏʀs Sᴏᴜʀᴄᴇ Lɪɴᴋ",
                            content=source_link,
                        )["path"]
                        buttons.buildbutton(
                            "🔗 Sᴏᴜʀᴄᴇ Lɪɴᴋ 🔗", f"https://telegra.ph/{telegraph_link}"
                        )
                    else:
                        buttons.buildbutton("🔗 Sᴏᴜʀᴄᴇ Lɪɴᴋ 🔗", source_link)
                except IndexError as i:
                    LOGGER.info(
                        f"Unable to build button for Source Link {self.link} because: {str(i)}"
                    )
            msg = " #Leeched\n"
            msg += f"{jam}\n"
            msg += f"\n╭ 📂  Fʟᴇɴᴀᴍᴇ ⇢ <code>{escape(name)}</code>"
            msg += f"\n├ 🕹️ Sɪᴢᴇ ⇢ {size}"
            msg += f"\n├ 📚 Tᴏᴛᴀʟ Fɪʟᴇꜱ ⇢ {folders}"
            if typ != 0:
                msg += f"\n├ 💻 Cᴏʀʀᴜᴘᴛᴇᴅ Fɪʟᴇꜱ ⇢ {typ}"
            msg += f"\n╰ 📬 Lᴇᴇᴄʜᴇᴅ Bʏ ⇢ {self.tag}"
            msg += f"\n⏰ Eʟᴀᴘꜱᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.message.date.timestamp())}\n"
            if not files:
                reply_message = sendMarkup(
                    msg,
                    self.bot,
                    self.message,
                    InlineKeyboardMarkup(buttons.build_menu(2)),
                )
            else:
                if BOT_PM and self.message.chat.type != "private":
                    pmwarn_leech = f"\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ BOT PM."
                    try:
                        replymsg = bot.sendMessage(
                            chat_id=self.user_id,
                            text=msg,
                            reply_markup=InlineKeyboardMarkup(buttons.build_menu(2)),
                            parse_mode=ParseMode.HTML,
                        )
                        buttons.sbutton(
                            "Vɪᴇᴡ Fɪʟᴇ ɪɴ PM",
                            f"botpmfilebutton {self.user_id} {replymsg.message_id}",
                        )
                    except Exception as e:
                        LOGGER.warning(f"Unable to send message to PM: {str(e)}")
                elif self.message.chat.type == "private":
                    pmwarn_leech = ""
                else:
                    pmwarn_leech = ""
                if LEECH_LOG and self.message.chat.type != "private":
                    for i in LEECH_LOG:
                        try:
                            fmsg = ""
                            for index, (link, name) in enumerate(
                                files.items(), start=1
                            ):
                                fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                                if len(fmsg.encode() + msg.encode()) > 4000:
                                    sleep(1)
                                    replymsg = bot.sendMessage(
                                        chat_id=i,
                                        text=msg + fmsg,
                                        reply_markup=InlineKeyboardMarkup(
                                            buttons.build_menu(2)
                                        ),
                                        parse_mode=ParseMode.HTML,
                                    )
                                    fmsg = ""
                            if fmsg != "":
                                sleep(1)
                                replymsg = bot.sendMessage(
                                    chat_id=i,
                                    text=msg + fmsg,
                                    reply_markup=InlineKeyboardMarkup(
                                        buttons.build_menu(2)
                                    ),
                                    parse_mode=ParseMode.HTML,
                                )
                            if self.message.chat_id != i:
                                try:
                                    log_channel = LEECH_LOG_CHANNEL_LINK
                                    leech_chat_id = str(LEECH_LOG)[5:][:-1]
                                    leech_file = f"https://t.me/c/{leech_chat_id}/{replymsg.message_id}"
                                    logwarn_leech = f'\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ <a href="{log_channel}">Lᴇᴇᴄʜ Lᴏɢs Cʜᴀɴɴᴇʟ</a>.'
                                    logwarn_leech += f'\n Jᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴜsɪɴɢ ᴛʜᴇ ᴀʙᴏᴠᴇ ʟɪɴᴋ ᴛᴏ sᴇᴇ ʏᴏᴜʀ <a href="{leech_file}">Lᴇᴇᴄʜᴇᴅ Fɪʟᴇs</a>.'
                                except Exception as ex:
                                    LOGGER.warning(
                                        f"Error in logwarn_leech string : {str(ex)}"
                                    )
                                    logwarn_leech = "\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ Lᴇᴇᴄʜ Lᴏɢs Cʜᴀɴɴᴇʟ</a>."
                            else:
                                logwarn_leech = ""
                        except Exception as e:
                            LOGGER.warning(f"Error with Leech Logs Message: {str(e)}")
                elif self.message.chat.type == "private":
                    logwarn_leech = ""
                else:
                    logwarn_leech = ""
                reply_message = sendMarkup(
                    msg + pmwarn_leech + logwarn_leech + warnmsg,
                    self.bot,
                    self.message,
                    InlineKeyboardMarkup(buttons.build_menu(2)),
                )
            Thread(
                target=auto_delete_upload_message,
                args=(bot, self.message, reply_message),
            ).start()
        else:
            msg = " #Mirrored\n"
            msg += f"{jam}\n"
            msg += f"\n╭ 📂  Fʟᴇɴᴀᴍᴇ ⇢ <code>{escape(name)}</code>"
            msg += f"\n├ 🕹️ Sɪᴢᴇ ⇢ {size}"
            msg += f"\n├ 💻 Tʏᴘᴇ ⇢ {typ}"
            if ospath.isdir(f"{DOWNLOAD_DIR}{self.uid}/{name}"):
                msg += f"\n├ 📂 Sᴜʙ-Fᴏʟᴅᴇʀꜱ ⇢ {folders}"
                msg += f"\n├ 📚 ꜰɪʟᴇꜱ ⇢ {files}"
            msg += f"\n╰ 📬 Bʏ  ⇢ {self.tag}"
            msg += f"\n⏰ Eʟᴀᴘꜱᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.message.date.timestamp())}\n"
            buttons = ButtonMaker()
            link = short_url(link)
            buttons.buildbutton("☁️ Dʀɪᴠᴇ Lɪɴᴋ ☁️", link)
            LOGGER.info(f"Done Uploading {name}")
            if INDEX_URL is not None:
                url_path = rutils.quote(f"{name}")
                share_url = f"{INDEX_URL}/{url_path}"
                if ospath.isdir(f"{DOWNLOAD_DIR}/{self.uid}/{name}"):
                    share_url += "/"
                    share_url = short_url(share_url)
                    buttons.buildbutton("⚡ Iɴᴅᴇx Lɪɴᴋ ⚡", share_url)
                else:
                    share_url = short_url(share_url)
                    buttons.buildbutton("⚡ Iɴᴅᴇx Lɪɴᴋ ⚡", share_url)
                    if VIEW_LINK:
                        share_urls = f"{INDEX_URL}/{url_path}?a=view"
                        share_urls = short_url(share_urls)
                        buttons.buildbutton("🌐 Vɪᴇᴡ Lɪɴᴋ 🌐", share_urls)
            if BUTTON_FOUR_NAME is not None and BUTTON_FOUR_URL is not None:
                buttons.buildbutton(f"{BUTTON_FOUR_NAME}", f"{BUTTON_FOUR_URL}")
            if BUTTON_FIVE_NAME is not None and BUTTON_FIVE_URL is not None:
                buttons.buildbutton(f"{BUTTON_FIVE_NAME}", f"{BUTTON_FIVE_URL}")
            if BUTTON_SIX_NAME is not None and BUTTON_SIX_URL is not None:
                buttons.buildbutton(f"{BUTTON_SIX_NAME}", f"{BUTTON_SIX_URL}")
            if SOURCE_LINK is True and self.link != "":
                try:
                    source_link = f"{self.link}"
                    if is_magnet(source_link):
                        source_link += f"<br><br>💘 Sʜᴀʀᴇ Mᴀɢɴᴇᴛ Tᴏ <a href='http://t.me/share/url?url={quote(self.link)}'>Tᴇʟᴇɢʀᴀᴍ</a><br>"
                        telegraph_link = telegraph.create_page(
                            title="Dipesh Mɪʀʀᴏʀs Sᴏᴜʀᴄᴇ Lɪɴᴋ",
                            content=source_link,
                        )["path"]
                        buttons.buildbutton(
                            "🔗 Sᴏᴜʀᴄᴇ Lɪɴᴋ 🔗", f"https://telegra.ph/{telegraph_link}"
                        )
                    else:
                        buttons.buildbutton("🔗 Sᴏᴜʀᴄᴇ Lɪɴᴋ 🔗", source_link)
                except IndexError as i:
                    LOGGER.info(
                        f"Unable to build button for Source Link {self.link} because: {str(i)}"
                    )
            if BOT_PM and self.message.chat.type != "private":
                pmwarn_mirror = f"\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ BOT PM."
                try:
                    replymsg = bot.sendMessage(
                        chat_id=self.user_id,
                        text=msg,
                        reply_markup=InlineKeyboardMarkup(buttons.build_menu(2)),
                        parse_mode=ParseMode.HTML,
                    )
                    buttons.sbutton(
                        "Vɪᴇᴡ Fɪʟᴇ ɪɴ PM",
                        f"botpmfilebutton {self.user_id} {replymsg.message_id}",
                    )
                except Exception as e:
                    LOGGER.warning(f"Unable to send files to PM: {str(e)}")
            elif self.message.chat.type == "private":
                pmwarn_mirror = ""
            else:
                pmwarn_mirror = ""
            if MIRROR_LOGS and self.message.chat.type != "private":
                for i in MIRROR_LOGS:
                    try:
                        replymsg = bot.sendMessage(
                            chat_id=i,
                            text=msg,
                            reply_markup=InlineKeyboardMarkup(buttons.build_menu(2)),
                            parse_mode=ParseMode.HTML,
                        )
                        if self.message.chat_id != i:
                            try:
                                log_channel = MIRROR_LOGS_CHANNEL_LINK
                                mirror_chat_id = str(MIRROR_LOGS)[5:][:-1]
                                mirror_file = f"https://t.me/c/{mirror_chat_id}/{replymsg.message_id}"
                                logwarn_mirror = f'\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ <a href="{log_channel}">Mɪʀʀᴏʀ/Cʟᴏɴᴇ Lᴏɢs Cʜᴀɴɴᴇʟ</a>.'
                                logwarn_mirror += f'\n Jᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴜsɪɴɢ ᴛʜᴇ ᴀʙᴏᴠᴇ ʟɪɴᴋ ᴛᴏ sᴇᴇ ʏᴏᴜʀ <a href="{mirror_file}">Mɪʀʀᴏʀᴇᴅ Fɪʟᴇs</a>.'
                            except Exception as ex:
                                LOGGER.warning(
                                    f"Error in logwarn_mirror message: {str(ex)}"
                                )
                                logwarn_mirror = "\n I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ Mɪʀʀᴏʀ/Cʟᴏɴᴇ Lᴏɢs Cʜᴀɴɴᴇʟ</a>."
                    except Exception as e:
                        LOGGER.warning(f"Unable to send files to Mirror Logs: {str(e)}")
            elif self.message.chat.type == "private":
                logwarn_mirror = ""
            else:
                logwarn_mirror = ""
            reply_message = sendMarkup(
                msg + pmwarn_mirror + logwarn_mirror + warnmsg,
                self.bot,
                self.message,
                InlineKeyboardMarkup(buttons.build_menu(2)),
            )
            Thread(
                target=auto_delete_upload_message,
                args=(bot, self.message, reply_message),
            ).start()
            if self.isQbit and QB_SEED and not self.extract:
                if self.isZip:
                    try:
                        osremove(f"{DOWNLOAD_DIR}{self.uid}/{name}")
                    except Exception:
                        pass
                return
        clean_download(f"{DOWNLOAD_DIR}{self.uid}")
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onUploadError(self, error):
        reply_to = self.message.reply_to_message
        if reply_to is not None:
            try:
                Thread(
                    target=auto_delete_reply_message, args=(self.bot, self.message)
                ).start()
            except Exception:
                pass
        e_str = error.replace("<", "").replace(">", "")
        clean_download(f"{DOWNLOAD_DIR}{self.uid}")
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        elapsed_time = f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.message.date.timestamp())}"
        reply_message = sendMessage(
            f"{self.tag} \n{e_str} {elapsed_time}", self.bot, self.message
        )
        Thread(
            target=auto_delete_upload_message, args=(bot, self.message, reply_message)
        ).start()
        if count == 0:
            self.clean()
        else:
            update_all_messages()
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)


def _mirror(
    bot,
    message,
    isZip=False,
    extract=False,
    isQbit=False,
    isLeech=False,
    pswd=None,
    multi=0,
):
    buttons = ButtonMaker()
    bot_d = bot.get_me()
    bot_d.username
    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    f"<a>{message.from_user.id}</a>"
    if FSUB:
        try:
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
            Thread(
                target=auto_delete_message, args=(bot, message, reply_message)
            ).start()
            return
        except BaseException:
            pass
    if BOT_PM and message.chat.type != "private":
        try:
            msg1 = f"Added your Requested link to Download\n"
            send = bot.sendMessage(message.from_user.id, text=msg1)
            send.delete()
        except Exception as e:
            LOGGER.warning(e)
            bot_d = bot.get_me()
            b_uname = bot_d.username
            uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            botstart = f"http://t.me/{b_uname}"
            buttons.buildbutton("Click Here to Start Me", f"{botstart}")
            startwarn = (
                f"Dᴇᴀʀ {uname},\n\n<b>ɪ ꜰᴏᴜɴᴅ ᴛʜᴀᴛ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ꜱᴛᴀʀᴛᴇᴅ ᴍᴇ ɪɴ ᴘᴍ (ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ) ʏᴇᴛ.</b>\n\n"
                f"ꜰʀᴏᴍ ɴᴏᴡ ᴏɴ ɪ ᴡɪʟʟ ɢɪᴠᴇ ʟɪɴᴋ ᴀɴᴅ ʟᴇᴇᴄʜᴇᴅ ꜰɪʟᴇꜱ ɪɴ ᴘᴍ ᴀɴᴅ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ᴏɴʟʏ"
            )
            message = sendMarkup(
                startwarn, bot, message, InlineKeyboardMarkup(buttons.build_menu(2))
            )
            Thread(target=auto_delete_message, args=(bot, message, message)).start()
            return
    if isLeech and len(LEECH_LOG) == 0:
        try:
            text = "Eʀʀᴏʀ﹕ Lᴇᴇᴄʜ Fᴜɴᴄᴛɪᴏɴᴀʟɪᴛʏ ᴡɪʟʟ ɴᴏᴛ ᴡᴏʀᴋ\n Rᴇᴀsᴏɴ﹕ Yᴏᴜʀ Lᴇᴇᴄʜ Lᴏɢ ᴠᴀʀ ɪs ᴇᴍᴘᴛʏ.\n\nRᴇᴀᴅ ᴛʜᴇ README ꜰɪʟᴇ ɪᴛ's ᴛʜᴇʀᴇ ꜰᴏʀ ᴀ ʀᴇᴀsᴏɴ."
            reply_message = sendMessage(text, bot, message)
            LOGGER.error(
                "Leech Log var is Empty. Kindly add Chat id in Leech log to use Leech Functionality"
            )
            Thread(
                target=auto_delete_message, args=(bot, message, reply_message)
            ).start()
            return reply_message
        except Exception as err:
            LOGGER.error(f"Error: \n{err}")
    mesg = message.text.split("\n")
    message_args = mesg[0].split(maxsplit=1)
    name_args = mesg[0].split("|", maxsplit=1)
    qbitsel = False
    is_gdtot = False
    is_driveapp = False
    is_appdrive = False
    is_hubdrive = False
    is_drivehub = False
    is_kolop = False
    is_drivebuzz = False
    is_gdflix = False
    is_drivesharer = False
    is_drivebit = False
    is_drivelink = False
    is_katdrive = False
    is_gadrive = False
    is_jiodrive = False
    is_drivefire = False
    is_sharerpw = False
    is_gplinks = False
    is_droplink = False
    if len(message_args) > 1:
        link = message_args[1].strip()
        if link.startswith("s ") or link == "s":
            qbitsel = True
            message_args = mesg[0].split(maxsplit=2)
            if len(message_args) > 2:
                link = message_args[2].strip()
            else:
                link = ""
        elif link.isdigit():
            multi = int(link)
            link = ""
        if link.startswith(("|", "pswd:")):
            link = ""
    else:
        link = ""

    if len(name_args) > 1:
        name = name_args[1]
        name = name.split(" pswd:")[0]
        name = name.strip()
    else:
        name = ""

    link = re_split(r"pswd:|\|", link)[0]
    link = link.strip()

    pswd_arg = mesg[0].split(" pswd: ")
    if len(pswd_arg) > 1:
        pswd = pswd_arg[1]

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    reply_to = message.reply_to_message
    if reply_to is not None:
        file = None
        media_array = [reply_to.document, reply_to.video, reply_to.audio]
        for i in media_array:
            if i is not None:
                file = i
                break

        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

        if not is_url(link) and not is_magnet(link) or len(link) == 0:
            if file is None:
                reply_text = reply_to.text
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_text.strip()
            elif file.mime_type != "application/x-bittorrent" and not isQbit:
                listener = MirrorListener(
                    bot, message, isZip, extract, isQbit, isLeech, pswd, tag, link
                )
                Thread(
                    target=TelegramDownloadHelper(listener).add_download,
                    args=(message, f"{DOWNLOAD_DIR}{listener.uid}/", name),
                ).start()
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
                    nextmsg = sendMessage(message_args[0], bot, nextmsg)
                    nextmsg.from_user.id = message.from_user.id
                    multi -= 1
                    sleep(4)
                    Thread(
                        target=_mirror,
                        args=(
                            bot,
                            nextmsg,
                            isZip,
                            extract,
                            isQbit,
                            isLeech,
                            pswd,
                            multi,
                        ),
                    ).start()
                return
            else:
                link = file.get_file().file_path

    if not is_url(link) and not is_magnet(link) and not ospath.exists(link):
        help_msg = "<b>Send link along with command line:</b>"
        help_msg += "\n<code>/command</code> {link} |newname pswd: xx [zip/unzip]"
        help_msg += "\n\n<b>By replying to link or file:</b>"
        help_msg += "\n<code>/command</code> |newname pswd: xx [zip/unzip]"
        help_msg += "\n\n<b>Direct link authorization:</b>"
        help_msg += (
            "\n<code>/command</code> {link} |newname pswd: xx\nusername\npassword"
        )
        help_msg += "\n\n<b>Qbittorrent selection:</b>"
        help_msg += (
            "\n<code>/qbcommand</code> <b>s</b> {link} or by replying to {file/link}"
        )
        help_msg += "\n\n<b>Multi links only by replying to first link or file:</b>"
        help_msg += "\n<code>/command</code> 10(number of links/files)\n\n<b>⚠⁉ If You Don't Know How To Use Bots, Check Others Message. Don't Play With Commands</b>"
        return sendMessage(help_msg, bot, message)

    LOGGER.info(link)
    listener = MirrorListener(
        bot, message, isZip, extract, isQbit, isLeech, pswd, tag, link
    )
    if (
        not is_mega_link(link)
        and not isQbit
        and not is_magnet(link)
        and not is_gdrive_link(link)
        and not link.endswith(".torrent")
    ):
        content_type = get_content_type(link)
        if content_type is None or re_match(r"text/html|text/plain", content_type):
            try:
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
                link = direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith("ERROR:"):
                    reply_message = sendMessage(str(e), bot, message)
                    Thread(
                        target=auto_delete_upload_message,
                        args=(bot, message, reply_message),
                    ).start()
                    return reply_message

    if is_gdrive_link(link):
        if not isZip and not extract and not isLeech:
            help_msg = (
                f"Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n"
            )
            help_msg += f"Use /{BotCommands.ZipMirrorCommand} to make zip of Google Drive folder\n\n"
            help_msg += f"Use /{BotCommands.UnzipMirrorCommand} to extracts Google Drive archive file"
            reply_message = sendMessage(help_msg, bot, message)
            Thread(
                target=auto_delete_upload_message, args=(bot, message, reply_message)
            ).start()
            return reply_message
        else:
            Thread(
                target=add_gd_download,
                args=(
                    link,
                    listener,
                    is_gdtot,
                    is_driveapp,
                    is_appdrive,
                    is_hubdrive,
                    is_drivehub,
                    is_kolop,
                    is_drivebuzz,
                    is_gdflix,
                    is_drivesharer,
                    is_drivebit,
                    is_drivelink,
                    is_katdrive,
                    is_gadrive,
                    is_jiodrive,
                    is_drivefire,
                    is_sharerpw,
                    is_gplinks,
                    is_droplink,
                ),
            ).start()
    elif is_mega_link(link):
        if MEGA_KEY is not None:
            Thread(
                target=MegaDownloader(listener).add_download,
                args=(link, f"{DOWNLOAD_DIR}{listener.uid}/"),
            ).start()
        else:
            sendMessage("MEGA_API_KEY not Provided!", bot, message)
    elif isQbit:
        Thread(
            target=QbDownloader(listener).add_qb_torrent,
            args=(link, f"{DOWNLOAD_DIR}{listener.uid}", qbitsel),
        ).start()
    else:
        if len(mesg) > 1:
            try:
                ussr = mesg[1]
            except Exception:
                ussr = ""
            try:
                pssw = mesg[2]
            except Exception:
                pssw = ""
            auth = f"{ussr}:{pssw}"
            auth = "Basic " + b64encode(auth.encode()).decode("ascii")
        else:
            auth = ""
        Thread(
            target=add_aria2c_download,
            args=(link, f"{DOWNLOAD_DIR}{listener.uid}", listener, name, auth),
        ).start()

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
        msg = message_args[0]
        if len(mesg) > 2:
            msg += "\n" + mesg[1] + "\n" + mesg[2]
        nextmsg = sendMessage(msg, bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        multi -= 1
        sleep(4)
        Thread(
            target=_mirror,
            args=(bot, nextmsg, isZip, extract, isQbit, isLeech, pswd, multi),
        ).start()


def bot_pm_button_handle(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split(" ")
    if user_id != int(data[1]):
        return query.answer(
            text="Since you didnt perform this task this file, you cant see it in your BOT PM",
            show_alert=True,
        )
    else:
        bot_d = context.bot.get_me()
        b_uname = bot_d.username
        boturl = f"https://t.me/{b_uname}?start={int(data[2])}"
        return query.answer(url=boturl)


def mirror(update, context):
    _mirror(context.bot, update.message)


def unzip_mirror(update, context):
    _mirror(context.bot, update.message, extract=True)


def zip_mirror(update, context):
    _mirror(context.bot, update.message, True)


def qb_mirror(update, context):
    _mirror(context.bot, update.message, isQbit=True)


def qb_unzip_mirror(update, context):
    _mirror(context.bot, update.message, extract=True, isQbit=True)


def qb_zip_mirror(update, context):
    _mirror(context.bot, update.message, True, isQbit=True)


def leech(update, context):
    _mirror(context.bot, update.message, isLeech=True)


def unzip_leech(update, context):
    _mirror(context.bot, update.message, extract=True, isLeech=True)


def zip_leech(update, context):
    _mirror(context.bot, update.message, True, isLeech=True)


def qb_leech(update, context):
    _mirror(context.bot, update.message, isQbit=True, isLeech=True)


def qb_unzip_leech(update, context):
    _mirror(context.bot, update.message, extract=True, isQbit=True, isLeech=True)


def qb_zip_leech(update, context):
    _mirror(context.bot, update.message, True, isQbit=True, isLeech=True)


mirror_handler = CommandHandler(
    BotCommands.MirrorCommand,
    mirror,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
unzip_mirror_handler = CommandHandler(
    BotCommands.UnzipMirrorCommand,
    unzip_mirror,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
zip_mirror_handler = CommandHandler(
    BotCommands.ZipMirrorCommand,
    zip_mirror,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
qb_mirror_handler = CommandHandler(
    BotCommands.QbMirrorCommand,
    qb_mirror,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
qb_unzip_mirror_handler = CommandHandler(
    BotCommands.QbUnzipMirrorCommand,
    qb_unzip_mirror,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
qb_zip_mirror_handler = CommandHandler(
    BotCommands.QbZipMirrorCommand,
    qb_zip_mirror,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
if LEECH_ENABLED:
    leech_handler = CommandHandler(
        BotCommands.LeechCommand,
        leech,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    unzip_leech_handler = CommandHandler(
        BotCommands.UnzipLeechCommand,
        unzip_leech,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    zip_leech_handler = CommandHandler(
        BotCommands.ZipLeechCommand,
        zip_leech,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    qb_leech_handler = CommandHandler(
        BotCommands.QbLeechCommand,
        qb_leech,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    qb_unzip_leech_handler = CommandHandler(
        BotCommands.QbUnzipLeechCommand,
        qb_unzip_leech,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
    qb_zip_leech_handler = CommandHandler(
        BotCommands.QbZipLeechCommand,
        qb_zip_leech,
        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
        run_async=True,
    )
else:
    leech_handler = CommandHandler(
        BotCommands.LeechCommand,
        leech,
        filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
        run_async=True,
    )
    unzip_leech_handler = CommandHandler(
        BotCommands.UnzipLeechCommand,
        unzip_leech,
        filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
        run_async=True,
    )
    zip_leech_handler = CommandHandler(
        BotCommands.ZipLeechCommand,
        zip_leech,
        filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
        run_async=True,
    )
    qb_leech_handler = CommandHandler(
        BotCommands.QbLeechCommand,
        qb_leech,
        filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
        run_async=True,
    )
    qb_unzip_leech_handler = CommandHandler(
        BotCommands.QbUnzipLeechCommand,
        qb_unzip_leech,
        filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
        run_async=True,
    )
    qb_zip_leech_handler = CommandHandler(
        BotCommands.QbZipLeechCommand,
        qb_zip_leech,
        filters=CustomFilters.owner_filter | CustomFilters.authorized_user,
        run_async=True,
    )
botpmbutton = CallbackQueryHandler(
    bot_pm_button_handle, pattern="botpmfilebutton", run_async=True
)
dispatcher.add_handler(botpmbutton)
dispatcher.add_handler(mirror_handler)
dispatcher.add_handler(unzip_mirror_handler)
dispatcher.add_handler(zip_mirror_handler)
dispatcher.add_handler(qb_mirror_handler)
dispatcher.add_handler(qb_unzip_mirror_handler)
dispatcher.add_handler(qb_zip_mirror_handler)
dispatcher.add_handler(leech_handler)
dispatcher.add_handler(unzip_leech_handler)
dispatcher.add_handler(zip_leech_handler)
dispatcher.add_handler(qb_leech_handler)
dispatcher.add_handler(qb_unzip_leech_handler)
dispatcher.add_handler(qb_zip_leech_handler)
