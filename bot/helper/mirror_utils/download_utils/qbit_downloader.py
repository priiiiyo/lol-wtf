from os import listdir
from os import path as ospath
from threading import Thread
from time import sleep, time

from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from bot import (
    BASE_URL,
    LOGGER,
    QB_SEED,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    TORRENT_DIRECT_LIMIT,
    TORRENT_TIMEOUT,
    WEB_PINCODE,
    ZIP_UNZIP_LIMIT,
    dispatcher,
    download_dict,
    download_dict_lock,
    get_client,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    getDownloadByGid,
    setInterval,
)
from bot.helper.ext_utils.fs_utils import (
    check_storage_threshold,
    clean_unwanted,
    get_base_name,
)
from bot.helper.mirror_utils.status_utils.qbit_download_status import QbDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    auto_delete_upload_message,
    deleteMessage,
    editMessage,
    sendMarkup,
    sendMessage,
    sendStatusMessage,
    update_all_messages,
)


class QbDownloader:
    POLLING_INTERVAL = 3

    def __init__(self, listener):
        self.__listener = listener
        self.__path = ""
        self.__name = ""
        self.select = False
        self.client = None
        self.periodic = None
        self.ext_hash = ""
        self.__stalled_time = time()
        self.__uploaded = False
        self.is_seeding = False
        self.__sizeChecked = False
        self.__dupChecked = False
        self.__rechecked = False

    def add_qb_torrent(self, link, path, select):
        self.__path = path
        self.select = select
        self.client = get_client()
        try:
            op = self.client.torrents_add(
                link,
                save_path=path,
                tags=self.__listener.uid,
                headers={"user-agent": "Wget/1.12"},
            )
            sleep(0.3)
            if op.lower() == "ok.":
                tor_info = self.client.torrents_info(tag=self.__listener.uid)
                if len(tor_info) == 0:
                    while True:
                        tor_info = self.client.torrents_info(tag=self.__listener.uid)
                        if len(tor_info) > 0:
                            break
                        elif time() - self.__stalled_time >= 12:
                            reply_message = sendMessage(
                                "Tʜɪs Tᴏʀʀᴇɴᴛ ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ ᴏʀ ɴᴏᴛ ᴀ ᴛᴏʀʀᴇɴᴛ. Iꜰ sᴏᴍᴇᴛʜɪɴɢ ᴡʀᴏɴɢ ᴘʟᴇᴀsᴇ ʀᴇᴘᴏʀᴛ.",
                                self.__listener.bot,
                                self.__listener.message,
                            )
                            Thread(
                                target=auto_delete_message,
                                args=(
                                    self.__listener.bot,
                                    self.__listener.message,
                                    reply_message,
                                ),
                            ).start()
                            return self.client.auth_log_out()
            else:
                reply_message = sendMessage(
                    "Tʜɪs ɪs ᴀɴ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ/ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ.",
                    self.__listener.bot,
                    self.__listener.message,
                )
                Thread(
                    target=auto_delete_message,
                    args=(self.__listener.bot, self.__listener.message, reply_message),
                ).start()
                return self.client.auth_log_out()
            tor_info = tor_info[0]
            self.__name = tor_info.name
            self.ext_hash = tor_info.hash
            with download_dict_lock:
                download_dict[self.__listener.uid] = QbDownloadStatus(
                    self.__listener, self
                )
            self.__listener.onDownloadStart()
            LOGGER.info(f"QbitDownload started: {self.__name} - Hash: {self.ext_hash}")
            self.periodic = setInterval(self.POLLING_INTERVAL, self.__qb_listener)
            if BASE_URL is not None and select:
                if link.startswith("magnet:"):
                    metamsg = "Dᴏᴡɴʟᴏᴀᴅɪɴɢ Mᴇᴛᴀᴅᴀᴛᴀ, ᴡᴀɪᴛ ᴛʜᴇɴ ʏᴏᴜ ᴄᴀɴ sᴇʟᴇᴄᴛ ꜰɪʟᴇs ᴏʀ ᴍɪʀʀᴏʀ ᴛᴏʀʀᴇɴᴛ ꜰɪʟᴇ"
                    meta = sendMessage(
                        metamsg, self.__listener.bot, self.__listener.message
                    )
                    while True:
                        tor_info = self.client.torrents_info(
                            torrent_hashes=self.ext_hash
                        )
                        if len(tor_info) == 0:
                            return deleteMessage(self.__listener.bot, meta)
                        try:
                            tor_info = tor_info[0]
                            if tor_info.state not in [
                                "metaDL",
                                "checkingResumeData",
                                "pausedDL",
                            ]:
                                deleteMessage(self.__listener.bot, meta)
                                break
                        except Exception:
                            return deleteMessage(self.__listener.bot, meta)
                self.client.torrents_pause(torrent_hashes=self.ext_hash)
                pincode = ""
                for n in str(self.ext_hash):
                    if n.isdigit():
                        pincode += str(n)
                    if len(pincode) == 4:
                        break
                buttons = button_build.ButtonMaker()
                gid = self.ext_hash[:12]
                if WEB_PINCODE:
                    buttons.buildbutton(
                        "Sᴇʟᴇᴄᴛ Fɪʟᴇs", f"{BASE_URL}/app/files/{self.ext_hash}"
                    )
                    buttons.sbutton("Pɪɴᴄᴏᴅᴇ", f"qbs pin {gid} {pincode}")
                else:
                    buttons.buildbutton(
                        "Sᴇʟᴇᴄᴛ Fɪʟᴇs",
                        f"{BASE_URL}/app/files/{self.ext_hash}?pin_code={pincode}",
                    )
                buttons.sbutton("Dᴏɴᴇ Sᴇʟᴇᴄᴛɪɴɢ", f"qbs done {gid} {self.ext_hash}")
                buttons.sbutton(
                    "Cᴀɴᴄᴇʟ", f"qbs cancel {gid} {self.__listener.message.message_id}"
                )
                QBBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
                msg = "Yᴏᴜʀ ᴅᴏᴡɴʟᴏᴀᴅ ᴘᴀᴜsᴇᴅ. Cʜᴏᴏsᴇ ꜰɪʟᴇs ᴛʜᴇɴ ᴘʀᴇss Dᴏɴᴇ Sᴇʟᴇᴄᴛɪɴɢ ʙᴜᴛᴛᴏɴ ᴛᴏ sᴛᴀʀᴛ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ. \nYᴏᴜʀ ᴅᴏᴡɴʟᴏᴀᴅ ᴡɪʟʟ sᴛᴀʀᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ɪɴ 2 Mɪɴᴜᴛᴇs "
                reply_message = sendMarkup(
                    msg, self.__listener.bot, self.__listener.message, QBBUTTONS
                )
                Thread(
                    target=self._auto_start, args=(gid, self.ext_hash, reply_message)
                ).start()
            else:
                sendStatusMessage(self.__listener.message, self.__listener.bot)
        except Exception as e:
            reply_message = sendMessage(
                str(e), self.__listener.bot, self.__listener.message
            )
            Thread(
                target=auto_delete_upload_message,
                args=(self.__listener.bot, self.__listener.message, reply_message),
            ).start()
            self.client.auth_log_out()

    def __qb_listener(self):
        try:
            tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
            if len(tor_info) == 0:
                return
            tor_info = tor_info[0]
            if tor_info.state == "metaDL":
                self.__stalled_time = time()
                if (
                    TORRENT_TIMEOUT is not None
                    and time() - tor_info.added_on >= TORRENT_TIMEOUT
                ):
                    self.__onDownloadError("Dead Torrent!")
            elif tor_info.state == "downloading":
                self.__stalled_time = time()
                if (
                    not self.__dupChecked
                    and STOP_DUPLICATE
                    and ospath.isdir(f"{self.__path}")
                    and not self.__listener.isLeech
                ):
                    LOGGER.info("Checking File/Folder if already in Drive")
                    qbname = str(listdir(f"{self.__path}")[-1])
                    if qbname.endswith(".!qB"):
                        qbname = ospath.splitext(qbname)[0]
                    if self.__listener.isZip:
                        qbname = f"{qbname}.zip"
                    elif self.__listener.extract:
                        try:
                            qbname = get_base_name(qbname)
                        except Exception:
                            qbname = None
                    if qbname is not None:
                        qbmsg, button = GoogleDriveHelper().drive_list(qbname, True)
                        if qbmsg:
                            elapsed_time += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.__listener.message.date.timestamp())}\n"
                            self.__onDownloadError(
                                "Fɪʟᴇ/Fᴏʟᴅᴇʀ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ Dʀɪᴠᴇ"
                            )
                            sendMarkup(
                                f"Hᴇʀᴇ ᴀʀᴇ ᴛʜᴇ sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs﹕ {elapsed_time}",
                                self.__listener.bot,
                                self.__listener.message,
                                button,
                            )
                    self.__dupChecked = True
                if not self.__sizeChecked:
                    size = tor_info.size
                    arch = any([self.__listener.isZip, self.__listener.extract])
                    if STORAGE_THRESHOLD is not None:
                        acpt = check_storage_threshold(size, arch)
                        if not acpt:
                            msg = f"Yᴏᴜ ᴍᴜsᴛ ʟᴇᴀᴠᴇ {STORAGE_THRESHOLD}GB ꜰʀᴇᴇ sᴛᴏʀᴀɢᴇ."
                            msg += f"\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}"
                            msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.__listener.message.date.timestamp())}\n"
                            return self.__onDownloadError(msg)
                    limit = None
                    if ZIP_UNZIP_LIMIT is not None and arch:
                        mssg = f"Zɪᴘ/Uɴᴢɪᴘ ʟɪᴍɪᴛ ɪs {ZIP_UNZIP_LIMIT}GB"
                        limit = ZIP_UNZIP_LIMIT
                    elif TORRENT_DIRECT_LIMIT is not None:
                        mssg = f"Tᴏʀʀᴇɴᴛ/Dɪʀᴇᴄᴛ ʟɪᴍɪᴛ ɪs {TORRENT_DIRECT_LIMIT}GB"
                        limit = TORRENT_DIRECT_LIMIT
                    if limit is not None:
                        LOGGER.info("Checking File/Folder Size...")
                        if size > limit * 1024**3:
                            fmsg = f"{mssg}.\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}"
                            self.__onDownloadError(fmsg)
                    self.__sizeChecked = True
            elif tor_info.state == "stalledDL":
                if not self.__rechecked and 0.99989999999999999 < tor_info.progress < 1:
                    msg = f"Fᴏʀᴄᴇ ʀᴇᴄʜᴇᴄᴋ ⁻ Nᴀᴍᴇ﹕ {self.__name} Hᴀsʜ﹕ "
                    msg += f"{self.ext_hash} Dᴏᴡɴʟᴏᴀᴅᴇᴅ Bʏᴛᴇs﹕ {tor_info.downloaded} "
                    msg += f"Sɪᴢᴇ﹕ {tor_info.size} Tᴏᴛᴀʟ Sɪᴢᴇ﹕ {tor_info.total_size}"
                    LOGGER.info(msg)
                    self.client.torrents_recheck(torrent_hashes=self.ext_hash)
                    self.__rechecked = True
                elif (
                    TORRENT_TIMEOUT is not None
                    and time() - self.__stalled_time >= TORRENT_TIMEOUT
                ):
                    self.__onDownloadError("Mᴀɢɴᴇᴛ/Tᴏʀʀᴇɴᴛ Lɪɴᴋ Is Dᴇᴀᴅ ❌")
            elif (
                (tor_info.state.lower().endswith("up") or tor_info.state == "uploading")
                and not self.__uploaded
                and len(listdir(self.__path)) != 0
            ):
                self.__uploaded = True
                if not QB_SEED:
                    self.client.torrents_pause(torrent_hashes=self.ext_hash)
                if self.select:
                    clean_unwanted(self.__path)
                self.__listener.onDownloadComplete()
                if (
                    QB_SEED
                    and not self.__listener.isLeech
                    and not self.__listener.extract
                ):
                    with download_dict_lock:
                        if self.__listener.uid not in list(download_dict.keys()):
                            self.client.torrents_delete(
                                torrent_hashes=self.ext_hash, delete_files=True
                            )
                            self.client.auth_log_out()
                            self.periodic.cancel()
                            return
                        download_dict[self.__listener.uid] = QbDownloadStatus(
                            self.__listener, self
                        )
                    self.is_seeding = True
                    update_all_messages()
                    LOGGER.info(f"Seeding started: {self.__name}")
                else:
                    self.client.torrents_delete(
                        torrent_hashes=self.ext_hash, delete_files=True
                    )
                    self.client.auth_log_out()
                    self.periodic.cancel()
            elif tor_info.state == "pausedUP" and QB_SEED:
                self.__listener.onUploadError(
                    f"Sᴇᴇᴅɪɴɢ sᴛᴏᴘᴘᴇᴅ ᴡɪᴛʜ Rᴀᴛɪᴏ﹕ {round(tor_info.ratio, 3)} ᴀɴᴅ Tɪᴍᴇ﹕ {get_readable_time(tor_info.seeding_time)}"
                )
                self.client.torrents_delete(
                    torrent_hashes=self.ext_hash, delete_files=True
                )
                self.client.auth_log_out()
                self.periodic.cancel()
        except Exception as e:
            LOGGER.error(str(e))

    def __onDownloadError(self, err):
        LOGGER.info(f"Cancelling Download: {self.__name}")
        self.client.torrents_pause(torrent_hashes=self.ext_hash)
        sleep(0.3)
        self.__listener.onDownloadError(err)
        self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
        self.client.auth_log_out()
        self.periodic.cancel()

    def cancel_download(self):
        if self.is_seeding:
            LOGGER.info(f"Cancelling Seed: {self.__name}")
            self.client.torrents_pause(torrent_hashes=self.ext_hash)
        else:
            self.__onDownloadError("Dᴏᴡɴʟᴏᴀᴅ Sᴛᴏᴘᴘᴇᴅ Bʏ Usᴇʀ﹗")

    def _auto_start(self, gid, ext_hash, msg):
        sleep(120)
        try:
            qbdl = getDownloadByGid(gid)
            qbdl.client().torrents_resume(torrent_hashes=ext_hash)
            sendStatusMessage(qbdl.listener().message, qbdl.listener().bot)
            deleteMessage(self.__listener.bot, msg)
        except Exception as e:
            LOGGER.error(f"{str(e)}")


def get_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    msg = query.message
    data = data.split()
    qbdl = getDownloadByGid(data[2])
    if user_id != qbdl.listener().message.from_user.id:
        query.answer(text="This task is not for you!", show_alert=True)
        return
    elif data[1] == "pin":
        query.answer(text=data[3], show_alert=True)
        return
    elif data[1] == "done":
        query.answer()
        qbdl.client().torrents_resume(torrent_hashes=data[3])
        sendStatusMessage(qbdl.listener().message, qbdl.listener().bot)
        query.message.delete()
        return
    elif data[1] == "cancel":
        query.answer()
        reply_message = editMessage("Tᴀsᴋ ʜᴀs ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ..", msg)
        Thread(
            target=auto_delete_message,
            args=(context.bot, query.message, reply_message),
        ).start()
        qbdl.download().cancel_download()
        return reply_message


qbs_handler = CallbackQueryHandler(get_confirm, pattern="qbs", run_async=True)
dispatcher.add_handler(qbs_handler)
