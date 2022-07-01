from random import SystemRandom
from string import ascii_letters, digits
from threading import Thread
from time import time

from bot import (
    LOGGER,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    TORRENT_DIRECT_LIMIT,
    ZIP_UNZIP_LIMIT,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import check_storage_threshold, get_base_name
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (
    auto_delete_upload_message,
    sendMarkup,
    sendMessage,
    sendStatusMessage,
)


def add_gd_download(
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
):
    res, size, name, files = GoogleDriveHelper().helper(link)
    if res != "":
        res += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() -listener.message.date.timestamp())}\n"
        reply_message = sendMessage(res, listener.bot, listener.message)
        Thread(
            target=auto_delete_upload_message,
            args=(listener.bot, listener.message, reply_message),
        ).start()
        return reply_message
    if STOP_DUPLICATE and not listener.isLeech:
        LOGGER.info("Checking File/Folder if already in Drive...")
        if listener.isZip:
            gname = f"{name}.zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except Exception:
                gname = None
        if gname is not None:
            gmsg, button = GoogleDriveHelper().drive_list(gname, True)
            if gmsg:
                msg = "Fɪʟᴇ/Fᴏʟᴅᴇʀ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ Dʀɪᴠᴇ.\nHᴇʀᴇ ᴀʀᴇ ᴛʜᴇ sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs﹕ "
                msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - listener.message.date.timestamp())}\n"
                reply_message = sendMarkup(msg, listener.bot, listener.message, button)
                Thread(
                    target=auto_delete_upload_message,
                    args=(listener.bot, listener.message, reply_message),
                ).start()
                return reply_message
    if any([ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD, TORRENT_DIRECT_LIMIT]):
        arch = any([listener.extract, listener.isZip])
        limit = None
        if STORAGE_THRESHOLD is not None:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f"Yᴏᴜ ᴍᴜsᴛ ʟᴇᴀᴠᴇ {STORAGE_THRESHOLD}GB ꜰʀᴇᴇ sᴛᴏʀᴀɢᴇ."
                msg += f"\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}"
                msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - listener.message.date.timestamp())}\n"
                reply_message = sendMessage(msg, listener.bot, listener.message)
                Thread(
                    target=auto_delete_upload_message,
                    args=(listener.bot, listener.message, reply_message),
                ).start()
                return reply_message
        if ZIP_UNZIP_LIMIT is not None and arch:
            mssg = f"Zɪᴘ/Uɴᴢɪᴘ ʟɪᴍɪᴛ ɪs {ZIP_UNZIP_LIMIT}GB"
            limit = ZIP_UNZIP_LIMIT
        elif TORRENT_DIRECT_LIMIT is not None:
            mssg = f"Tᴏʀʀᴇɴᴛ/Dɪʀᴇᴄᴛ ʟɪᴍɪᴛ ɪs {TORRENT_DIRECT_LIMIT}GB"
            limit = TORRENT_DIRECT_LIMIT
        if limit is not None:
            LOGGER.info("Checking File/Folder Size...")
            if size > limit * 1024**3:
                msg = (
                    f"{mssg}.\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}."
                )
                msg += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - listener.message.date.timestamp())}\n"
                reply_message = sendMessage(msg, listener.bot, listener.message)
                Thread(
                    target=auto_delete_upload_message,
                    args=(listener.bot, listener.message, reply_message),
                ).start()
                return reply_message
    LOGGER.info(f"Download Name: {name}")
    drive = GoogleDriveHelper(name, listener)
    gid = "".join(SystemRandom().choices(ascii_letters + digits, k=12))
    download_status = GdDownloadStatus(drive, size, listener, gid)
    with download_dict_lock:
        download_dict[listener.uid] = download_status
    listener.onDownloadStart()
    sendStatusMessage(listener.message, listener.bot)
    drive.download(link)
    LOGGER.info(f"Deleting: {link}")
    if is_gdtot:
        drive.deletefile(link)
    elif is_appdrive:
        drive.deletefile(link)
    elif is_driveapp:
        drive.deletefile(link)
    elif is_hubdrive:
        drive.deletefile(link)
    elif is_drivehub:
        drive.deletefile(link)
    elif is_kolop:
        drive.deletefile(link)
    elif is_drivebuzz:
        drive.deletefile(link)
    elif is_gdflix:
        drive.deletefile(link)
    elif is_drivesharer:
        drive.deletefile(link)
    elif is_drivebit:
        drive.deletefile(link)
    elif is_katdrive:
        drive.deletefile(link)
    elif is_drivefire:
        drive.deletefile(link)
    elif is_gadrive:
        drive.deletefile(link)
    elif is_jiodrive:
        drive.deletefile(link)
    elif is_drivelink:
        drive.deletefile(link)
    elif is_sharerpw:
        drive.deletefile(link)
    elif is_gplinks:
        drive.deletefile(link)
    elif is_droplink:
        drive.deletefile(link)
