#!/usr/bin/env python3
from logging import WARNING, getLogger
from threading import Lock, RLock, Thread
from time import time

from bot import (
    LOGGER,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    app,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (
    auto_delete_upload_message,
    sendMarkup,
    sendStatusMessage,
)

from ..status_utils.telegram_download_status import TelegramDownloadStatus

global_lock = Lock()
GLOBAL_GID = set()
getLogger("pyrogram").setLevel(WARNING)


class TelegramDownloadHelper:
    def __init__(self, listener):
        self.name = ""
        self.size = 0
        self.progress = 0
        self.downloaded_bytes = 0
        self.__start_time = time()
        self.__listener = listener
        self.__id = ""
        self.__is_cancelled = False
        self.__resource_lock = RLock()

    @property
    def download_speed(self):
        with self.__resource_lock:
            return self.downloaded_bytes / (time() - self.__start_time)

    def __onDownloadStart(self, name, size, file_id):
        with global_lock:
            GLOBAL_GID.add(file_id)
        with self.__resource_lock:
            self.name = name
            self.size = size
            self.__id = file_id
        with download_dict_lock:
            download_dict[self.__listener.uid] = TelegramDownloadStatus(
                self, self.__listener, self.__id
            )
        self.__listener.onDownloadStart()
        sendStatusMessage(self.__listener.message, self.__listener.bot)

    def __onDownloadProgress(self, current, total):
        if self.__is_cancelled:
            app.stop_transmission()
            return
        with self.__resource_lock:
            self.downloaded_bytes = current
            try:
                self.progress = current / self.size * 100
            except ZeroDivisionError:
                pass

    def __onDownloadError(self, error):
        with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except Exception:
                pass
        self.__listener.onDownloadError(error)

    def __onDownloadComplete(self):
        with global_lock:
            GLOBAL_GID.remove(self.__id)
        self.__listener.onDownloadComplete()

    def __download(self, message, path):
        try:
            download = message.download(
                file_name=path, progress=self.__onDownloadProgress
            )
        except Exception as e:
            LOGGER.error(str(e))
            return self.__onDownloadError(str(e))
        if download is not None:
            self.__onDownloadComplete()
        elif not self.__is_cancelled:
            self.__onDownloadError("Iɴᴛᴇʀɴᴀʟ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ")

    def add_download(self, message, path, filename):
        _dmsg = app.get_messages(
            message.chat.id, reply_to_message_ids=message.message_id
        )
        media_array = [_dmsg.document, _dmsg.video, _dmsg.audio]
        for i in media_array:
            if i is not None:
                media = i
                break
        if media is not None:
            with global_lock:
                # For avoiding locking the thread lock for long time
                # unnecessarily
                download = media.file_unique_id not in GLOBAL_GID
            if filename == "":
                name = media.file_name
            else:
                name = filename
                path = path + name

            if download:
                size = media.file_size
                if STOP_DUPLICATE and not self.__listener.isLeech:
                    LOGGER.info("Checking File/Folder if already in Drive...")
                    smsg, button = GoogleDriveHelper().drive_list(name, True, True)
                    if smsg:
                        msg = "Fɪʟᴇ/Fᴏʟᴅᴇʀ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ Dʀɪᴠᴇ.\nHᴇʀᴇ ᴀʀᴇ ᴛʜᴇ sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs﹕"
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

                if STORAGE_THRESHOLD is not None:
                    arch = any([self.__listener.isZip, self.__listener.extract])
                    acpt = check_storage_threshold(size, arch)
                    if not acpt:
                        msg = f"Yᴏᴜ ᴍᴜsᴛ ʟᴇᴀᴠᴇ {STORAGE_THRESHOLD}GB ꜰʀᴇᴇ sᴛᴏʀᴀɢᴇ."
                        msg += (
                            f"\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}"
                        )
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

                self.__onDownloadStart(name, size, media.file_unique_id)
                LOGGER.info(
                    f"Downloading Telegram file with id: {media.file_unique_id}"
                )
                return self.__download(_dmsg, path)
            else:
                self.__onDownloadError("Fɪʟᴇ ᴀʟʀᴇᴀᴅʏ ʙᴇɪɴɢ ᴅᴏᴡɴʟᴏᴀᴅᴇᴅ﹗")
        else:
            self.__onDownloadError("Nᴏ ᴅᴏᴄᴜᴍᴇɴᴛ ɪɴ ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ")

    def cancel_download(self):
        LOGGER.info(f"Cancelling download on user request: {self.__id}")
        self.__is_cancelled = True
        self.__onDownloadError("Cᴀɴᴄᴇʟʟᴇᴅ Bʏ  Usᴇʀ﹗")
