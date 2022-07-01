from threading import Thread
from time import sleep, time

from bot import (
    LOGGER,
    STOP_DUPLICATE,
    STORAGE_THRESHOLD,
    TORRENT_DIRECT_LIMIT,
    ZIP_UNZIP_LIMIT,
    aria2,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    getDownloadByGid,
    is_magnet,
    new_thread,
)
from bot.helper.ext_utils.fs_utils import check_storage_threshold, get_base_name
from bot.helper.mirror_utils.status_utils.aria_download_status import AriaDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (
    auto_delete_upload_message,
    sendMarkup,
    sendMessage,
    sendStatusMessage,
)


@new_thread
def __onDownloadStarted(api, gid):
    try:
        if any(
            [STOP_DUPLICATE, TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD]
        ):
            download = api.get_download(gid)
            if download.is_metadata:
                LOGGER.info(f"onDownloadStarted: {gid} Metadata")
                return
            elif not download.is_torrent:
                sleep(3)
                download = api.get_download(gid)
            LOGGER.info(f"onDownloadStarted: {gid}")
            dl = getDownloadByGid(gid)
            if not dl:
                return
            if STOP_DUPLICATE and not dl.getListener().isLeech:
                LOGGER.info("Checking File/Folder if already in Drive...")
                sname = download.name
                if dl.getListener().isZip:
                    sname = f"{sname}.zip"
                elif dl.getListener().extract:
                    try:
                        sname = get_base_name(sname)
                    except Exception:
                        sname = None
                if sname is not None:
                    smsg, button = GoogleDriveHelper().drive_list(sname, True)
                    if smsg:
                        elapsed_time += f"\n\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - dl.getListener().message.date.timestamp())}\n"
                        dl.getListener().onDownloadError(
                            "Fɪʟᴇ/Fᴏʟᴅᴇʀ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ Dʀɪᴠᴇ.\n\n"
                        )
                        api.remove([download], force=True, files=True)
                        reply_message = sendMarkup(
                            f"Hᴇʀᴇ ᴀʀᴇ ᴛʜᴇ sᴇᴀʀᴄʜ ʀᴇsᴜʟᴛs﹕{elapsed_time}",
                            dl.getListener().bot,
                            dl.getListener().message,
                            button,
                        )
                        Thread(
                            target=auto_delete_upload_message,
                            args=(
                                dl.getListener().bot,
                                dl.getListener().message,
                                reply_message,
                            ),
                        ).start()
                        return reply_message
            if any([ZIP_UNZIP_LIMIT, TORRENT_DIRECT_LIMIT, STORAGE_THRESHOLD]):
                sleep(1)
                limit = None
                size = download.total_length
                arch = any([dl.getListener().isZip, dl.getListener().extract])
                if STORAGE_THRESHOLD is not None:
                    acpt = check_storage_threshold(size, arch, True)
                    # True if files allocated, if allocation disabled remove
                    # True arg
                    if not acpt:
                        msg = f"Yᴏᴜ ᴍᴜsᴛ ʟᴇᴀᴠᴇ {STORAGE_THRESHOLD}GB ꜰʀᴇᴇ sᴛᴏʀᴀɢᴇ."
                        msg += (
                            f"\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}"
                        )
                        dl.getListener().onDownloadError(msg)
                        return api.remove([download], force=True, files=True)
                if ZIP_UNZIP_LIMIT is not None and arch:
                    mssg = f"Zɪᴘ/Uɴᴢɪᴘ ʟɪᴍɪᴛ ɪs {ZIP_UNZIP_LIMIT}GB"
                    limit = ZIP_UNZIP_LIMIT
                elif TORRENT_DIRECT_LIMIT is not None:
                    mssg = f"Tᴏʀʀᴇɴᴛ/Dɪʀᴇᴄᴛ ʟɪᴍɪᴛ ɪs {TORRENT_DIRECT_LIMIT}GB"
                    limit = TORRENT_DIRECT_LIMIT
                if limit is not None:
                    LOGGER.info("Checking File/Folder Size...")
                    if size > limit * 1024**3:
                        dl.getListener().onDownloadError(
                            f"{mssg}.\nYᴏᴜʀ Fɪʟᴇ/Fᴏʟᴅᴇʀ sɪᴢᴇ ɪs {get_readable_file_size(size)}"
                        )
                        return api.remove([download], force=True, files=True)
    except Exception as e:
        LOGGER.error(
            f"{e} onDownloadStart: {gid} stop duplicate and size check didn't pass"
        )


@new_thread
def __onDownloadComplete(api, gid):
    LOGGER.info(f"onDownloadComplete: {gid}")
    dl = getDownloadByGid(gid)
    download = api.get_download(gid)
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f"Changed gid from {gid} to {new_gid}")
    elif dl:
        Thread(target=dl.getListener().onDownloadComplete).start()


@new_thread
def __onDownloadStopped(api, gid):
    sleep(6)
    if dl := getDownloadByGid(gid):
        dl.getListener().onDownloadError("Mᴀɢɴᴇᴛ/Tᴏʀʀᴇɴᴛ Lɪɴᴋ Is Dᴇᴀᴅ ❌")


@new_thread
def __onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    sleep(0.5)
    dl = getDownloadByGid(gid)
    try:
        download = api.get_download(gid)
        error = download.error_message
        LOGGER.info(f"Download Error: {error}")
    except Exception:
        pass
    if dl:
        dl.getListener().onDownloadError(error)


def start_listener():
    aria2.listen_to_notifications(
        threaded=True,
        on_download_start=__onDownloadStarted,
        on_download_error=__onDownloadError,
        on_download_stop=__onDownloadStopped,
        on_download_complete=__onDownloadComplete,
        timeout=20,
    )


def add_aria2c_download(link: str, path, listener, filename, auth):
    if is_magnet(link):
        download = aria2.add_magnet(link, {"dir": path})
    else:
        download = aria2.add_uris(
            [link], {"dir": path, "out": filename, "header": f"authorization: {auth}"}
        )
    if download.error_message:
        error = str(download.error_message).replace("<", " ").replace(">", " ")
        LOGGER.info(f"Download Error: {error}")
        reply_message = sendMessage(error, listener.bot, listener.message)
        Thread(
            target=auto_delete_upload_message,
            args=(listener.bot, listener.message, reply_message),
        ).start()
        return reply_message
    with download_dict_lock:
        download_dict[listener.uid] = AriaDownloadStatus(download.gid, listener)
        LOGGER.info(f"Started: {download.gid} DIR: {download.dir} ")
    listener.onDownloadStart()
    sendStatusMessage(listener.message, listener.bot)


start_listener()
