from pathlib import Path
from threading import Lock, Thread
from time import time

from megasdkrestclient import MegaSdkRestClient, constants

from bot import (
    LOGGER,
    MEGA_LIMIT,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    ZIP_UNZIP_LIMIT,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    setInterval,
)
from bot.helper.ext_utils.fs_utils import check_storage_threshold, get_base_name
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (
    auto_delete_upload_message,
    sendMarkup,
    sendMessage,
    sendStatusMessage,
)

from ..status_utils.mega_download_status import MegaDownloadStatus


class MegaDownloader:
    POLLING_INTERVAL = 3

    def __init__(self, listener):
        self.__listener = listener
        self.__name = ""
        self.__gid = ""
        self.__resource_lock = Lock()
        self.__mega_client = MegaSdkRestClient("http://localhost:6090")
        self.__periodic = None
        self.__downloaded_bytes = 0
        self.__progress = 0
        self.__size = 0

    @property
    def progress(self):
        with self.__resource_lock:
            return self.__progress

    @property
    def downloaded_bytes(self):
        with self.__resource_lock:
            return self.__downloaded_bytes

    @property
    def size(self):
        with self.__resource_lock:
            return self.__size

    @property
    def gid(self):
        with self.__resource_lock:
            return self.__gid

    @property
    def name(self):
        with self.__resource_lock:
            return self.__name

    @property
    def download_speed(self):
        if self.gid is not None:
            return self.__mega_client.getDownloadInfo(self.gid)["speed"]

    def __onDownloadStart(self, name, size, gid):
        self.__periodic = setInterval(self.POLLING_INTERVAL, self.__onInterval)
        with download_dict_lock:
            download_dict[self.__listener.uid] = MegaDownloadStatus(
                self, self.__listener
            )
        with self.__resource_lock:
            self.__name = name
            self.__size = size
            self.__gid = gid
        self.__listener.onDownloadStart()
        sendStatusMessage(self.__listener.message, self.__listener.bot)

    def __onInterval(self):
        dlInfo = self.__mega_client.getDownloadInfo(self.gid)
        if (
            dlInfo["state"]
            in [
                constants.State.TYPE_STATE_COMPLETED,
                constants.State.TYPE_STATE_CANCELED,
                constants.State.TYPE_STATE_FAILED,
            ]
            and self.__periodic is not None
        ):
            self.__periodic.cancel()
        if dlInfo["state"] == constants.State.TYPE_STATE_COMPLETED:
            self.__onDownloadComplete()
            return
        if dlInfo["state"] == constants.State.TYPE_STATE_CANCELED:
            self.__onDownloadError("Dᴏᴡɴʟᴏᴀᴅ Sᴛᴏᴘᴘᴇᴅ Bʏ Usᴇʀ﹗")
            return
        if dlInfo["state"] == constants.State.TYPE_STATE_FAILED:
            self.__onDownloadError(dlInfo["error_string"])
            return
        self.__onDownloadProgress(dlInfo["completed_length"], dlInfo["total_length"])

    def __onDownloadProgress(self, current, total):
        with self.__resource_lock:
            self.__downloaded_bytes = current
            try:
                self.__progress = current / total * 100
            except ZeroDivisionError:
                self.__progress = 0

    def __onDownloadError(self, error):
        self.__listener.onDownloadError(error)

    def __onDownloadComplete(self):
        self.__listener.onDownloadComplete()

    def add_download(self, link, path):
        Path(path).mkdir(parents=True, exist_ok=True)
        try:
            dl = self.__mega_client.addDl(link, path)
        except Exception as err:
            LOGGER.error(err)
            reply_message = sendMessage(
                str(err), self.__listener.bot, self.__listener.message
            )
            Thread(
                target=auto_delete_upload_message,
                args=(self.__listener.bot, self.__listener.message, reply_message),
            ).start()
            return reply_message
        gid = dl["gid"]
        info = self.__mega_client.getDownloadInfo(gid)
        file_name = info["name"]
        file_size = info["total_length"]
        if STOP_DUPLICATE and not self.__listener.isLeech:
            LOGGER.info("Checking File/Folder if already in Drive")
            mname = file_name
            if self.__listener.isZip:
                mname = f"{mname}.zip"
            elif self.__listener.extract:
                try:
                    mname = get_base_name(mname)
                except Exception:
                    mname = None
            if mname is not None:
                smsg, button = GoogleDriveHelper().drive_list(mname, True)
                if smsg:
                    msg1 = "Fɪʟᴇ/Fᴏʟᴅᴇʀ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ Dʀɪᴠᴇ.\nHᴇʀᴇ ᴀʀᴇ ᴛʜᴇ sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs﹕ "
                    msg1 += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.__listener.message.date.timestamp())}\n"
                    reply_message = sendMarkup(
                        msg1, self.__listener.bot, self.__listener.message, button
                    )
                    Thread(
                        target=auto_delete_upload_message,
                        args=(
                            self.__listener.bot,
                            self.__listener.message,
                            reply_message,
                        ),
                    ).start()
                    return reply_message
        if any([STORAGE_THRESHOLD, ZIP_UNZIP_LIMIT, MEGA_LIMIT]):
            arch = any([self.__listener.isZip, self.__listener.extract])
            if STORAGE_THRESHOLD is not None:
                acpt = check_storage_threshold(file_size, arch)
                if not acpt:
                    msg = f"Yᴏᴜ ᴍᴜsᴛ ʟᴇᴀᴠᴇ {STORAGE_THRESHOLD}GB ꜰʀᴇᴇ sᴛᴏʀᴀɢᴇ."
                    msg += f"\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(file_size)}"
                    msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.__listener.message.date.timestamp())}\n"
                    reply_message = sendMarkup(
                        msg, self.__listener.bot, self.__listener.message, button
                    )
                    Thread(
                        target=auto_delete_upload_message,
                        args=(
                            self.__listener.bot,
                            self.__listener.message,
                            reply_message,
                        ),
                    ).start()
                    return reply_message
            limit = None
            if ZIP_UNZIP_LIMIT is not None and arch:
                msg3 = f"Failed, Zɪᴘ/Uɴᴢɪᴘ ʟɪᴍɪᴛ ɪs {ZIP_UNZIP_LIMIT}GB.\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(file_size)}."
                limit = ZIP_UNZIP_LIMIT
            elif MEGA_LIMIT is not None:
                msg3 = f"Failed, Mega limit is {MEGA_LIMIT}GB.\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(file_size)}."
                limit = MEGA_LIMIT
            if limit is not None:
                LOGGER.info("Checking File/Folder Size...")
                if file_size > limit * 1024**3:
                    msg3 += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - self.__listener.message.date.timestamp())}\n"
                    reply_message = sendMarkup(
                        msg3, self.__listener.bot, self.__listener.message, button
                    )
                    Thread(
                        target=auto_delete_upload_message,
                        args=(
                            self.__listener.bot,
                            self.__listener.message,
                            reply_message,
                        ),
                    ).start()
                    return reply_message
        self.__onDownloadStart(file_name, file_size, gid)
        LOGGER.info(f"Mega download started with gid: {gid}")

    def cancel_download(self):
        LOGGER.info(f"Cancelling download on user request: {self.gid}")
        self.__mega_client.cancelDl(self.gid)
