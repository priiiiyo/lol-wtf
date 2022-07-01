from html import escape
from threading import Thread
from time import sleep, time
from urllib.parse import quote

from requests import get as rget
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (
    LOGGER,
    SEARCH_API_LINK,
    SEARCH_LIMIT,
    SEARCH_PLUGINS,
    dispatcher,
    get_client,
)
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from bot.helper.ext_utils.telegraph_helper import telegraph
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

if SEARCH_PLUGINS is not None:
    PLUGINS = []
    qbclient = get_client()
    if qb_plugins := qbclient.search_plugins():
        for plugin in qb_plugins:
            qbclient.search_uninstall_plugin(names=plugin["name"])
    qbclient.search_install_plugin(SEARCH_PLUGINS)
    qbclient.auth_log_out()

SITES = {
    "1337x": "1337x",
    "yts": "YTS",
    "tgx": "TorrentGalaxy",
    "torlock": "Torlock",
    "piratebay": "PirateBay",
    "nyaasi": "NyaaSi",
    "zooqle": "Zooqle",
    "kickass": "KickAss",
    "bitsearch": "Bitsearch",
    "glodls": "Glodls",
    "magnetdl": "MagnetDL",
    "limetorrent": "LimeTorrent",
    "torrentfunk": "TorrentFunk",
    "torrentproject": "TorrentProject",
    "libgen": "Libgen",
    "ybt": "YourBittorrent",
    "all": "All",
}

TELEGRAPH_LIMIT = 300


def torser(update, context):
    user_id = update.message.from_user.id
    buttons = button_build.ButtonMaker()
    if SEARCH_API_LINK is None and SEARCH_PLUGINS is None:
        reply_message = sendMessage(
            "Nᴏ API ʟɪɴᴋ ᴏʀ sᴇᴀʀᴄʜ PLUGINS ᴀᴅᴅᴇᴅ ꜰᴏʀ ᴛʜɪs ꜰᴜɴᴄᴛɪᴏɴ",
            context.bot,
            update.message,
        )
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
    elif len(context.args) == 0 and SEARCH_API_LINK is None:
        reply_message = sendMessage(
            "Sᴇɴᴅ ᴀ sᴇᴀʀᴄʜ ᴋᴇʏ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴄᴏᴍᴍᴀɴᴅ", context.bot, update.message
        )
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
    elif len(context.args) == 0:
        buttons.sbutton("Tʀᴇɴᴅɪɴɢ", f"torser {user_id} apitrend")
        buttons.sbutton("Rᴇᴄᴇɴᴛ", f"torser {user_id} apirecent")
        buttons.sbutton("Cᴀɴᴄᴇʟ", f"torser {user_id} cancel")
        button = InlineKeyboardMarkup(buttons.build_menu(2))
        reply_message = sendMarkup(
            "Sᴇɴᴅ ᴀ sᴇᴀʀᴄʜ ᴋᴇʏ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴄᴏᴍᴍᴀɴᴅ", context.bot, update.message, button
        )
        Thread(
            target=auto_delete_upload_message,
            args=(context.bot, update.message, reply_message),
        ).start()
    elif SEARCH_API_LINK is not None and SEARCH_PLUGINS is not None:
        buttons.sbutton("Aᴘɪ", f"torser {user_id} apisearch")
        buttons.sbutton("Pʟᴜɢɪɴs", f"torser {user_id} plugin")
        buttons.sbutton("Cᴀɴᴄᴇʟ", f"torser {user_id} cancel")
        button = InlineKeyboardMarkup(buttons.build_menu(2))
        reply_message = sendMarkup(
            "Cʜᴏᴏsᴇ ᴛᴏᴏʟ ᴛᴏ sᴇᴀʀᴄʜ ⇢ ", context.bot, update.message, button
        )
        Thread(
            target=auto_delete_upload_message,
            args=(context.bot, update.message, reply_message),
        ).start()
    elif SEARCH_API_LINK is not None:
        button = _api_buttons(user_id, "apisearch")
        reply_message = sendMarkup(
            "Cʜᴏᴏsᴇ sɪᴛᴇ ᴛᴏ sᴇᴀʀᴄʜ ⇢ ", context.bot, update.message, button
        )
        Thread(
            target=auto_delete_upload_message,
            args=(context.bot, update.message, reply_message),
        ).start()
    else:
        button = _plugin_buttons(user_id)
        reply_message = sendMarkup(
            "Cʜᴏᴏsᴇ sɪᴛᴇ ᴛᴏ sᴇᴀʀᴄʜ ⇢ ", context.bot, update.message, button
        )
        Thread(
            target=auto_delete_upload_message,
            args=(context.bot, update.message, reply_message),
        ).start()


def torserbut(update, context):
    msg = ""
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)
    key = key[1].strip() if len(key) > 1 else None
    data = query.data
    data = data.split()
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
    elif data[2].startswith("api"):
        query.answer()
        button = _api_buttons(user_id, data[2])
        editMessage("Cʜᴏᴏsᴇ Sɪᴛᴇ ⇢ ", message, button)
    elif data[2] == "plugin":
        query.answer()
        button = _plugin_buttons(user_id)
        editMessage("Cʜᴏᴏsᴇ Sɪᴛᴇ ⇢ ", message, button)
    elif data[2] != "cancel":
        query.answer()
        site = data[2]
        method = data[3]
        if method.startswith("api"):
            if key is None:
                if method == "apirecent":
                    endpoint = "Recent"
                elif method == "apitrend":
                    endpoint = "Trending"
                msg += f"<b>Lɪsᴛɪɴɢ {endpoint} Iᴛᴇᴍs... \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{SITES.get(site)}</i></b>"

            else:
                msg += f"<b>Sᴇᴀʀᴄʜɪɴɢ ꜰᴏʀ <i>{key}</i> \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{SITES.get(site)}</i></b>"

        else:
            msg += f"<b>Sᴇᴀʀᴄʜɪɴɢ ꜰᴏʀ <i>{key}</i> \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{site.capitalize()}</i></b>"
        editMessage(
            msg,
            message,
        )
        Thread(target=_search, args=(key, site, message, method)).start()
    else:
        query.answer()
        editMessage("Sᴇᴀʀᴄʜ ʜᴀs ʙᴇᴇɴ ᴄᴀɴᴄᴇʟᴇᴅ﹗", message)


def _search(key, site, message, method):
    if method.startswith("api"):
        if method == "apisearch":
            LOGGER.info(f"API Searching: {key} from {site}")
            if site == "all":
                api = f"{SEARCH_API_LINK}/api/v1/all/search?query={key}&limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/search?site={site}&query={key}&limit={SEARCH_LIMIT}"
        elif method == "apitrend":
            LOGGER.info(f"API Trending from {site}")
            if site == "all":
                api = f"{SEARCH_API_LINK}/api/v1/all/trending?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/trending?site={site}&limit={SEARCH_LIMIT}"
        elif method == "apirecent":
            LOGGER.info(f"API Recent from {site}")
            if site == "all":
                api = f"{SEARCH_API_LINK}/api/v1/all/recent?limit={SEARCH_LIMIT}"
            else:
                api = (
                    f"{SEARCH_API_LINK}/api/v1/recent?site={site}&limit={SEARCH_LIMIT}"
                )
        try:
            resp = rget(api)
            search_results = resp.json()
            if "error" in search_results.keys():
                elapsed_time = f"\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}"
                return editMessage(
                    f"Nᴏ ʀᴇsᴜʟᴛ ꜰᴏᴜɴᴅ ꜰᴏʀ <i>{key}</i> \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{SITES.get(site)}</i> {elapsed_time}",
                    message,
                )
            msg = f"<b>Fᴏᴜɴᴅ {min(search_results['total'], TELEGRAPH_LIMIT)}</b> \n"
            if method == "apitrend":
                msg += f" <b>Tʀᴇɴᴅɪɴɢ Rᴇsᴜʟᴛ(s) \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{SITES.get(site)}</i></b> \n"
            elif method == "apirecent":
                msg += f" <b>Rᴇᴄᴇɴᴛ Rᴇsᴜʟᴛ(s) \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{SITES.get(site)}</i></b>"
            else:
                msg += f" <b>Rᴇsᴜʟᴛ(s) 𝗳𝗼𝗿 <i>{key}</i> \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{SITES.get(site)}</i></b>"
            search_results = search_results["data"]
        except Exception as e:
            elapsed_time = f"\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}"
            return editMessage(str(e) + elapsed_time, message)
    else:
        LOGGER.info(f"PLUGINS Searching: {key} from {site}")
        client = get_client()
        search = client.search_start(
            pattern=str(key), plugins=str(site), category="all"
        )
        search_id = search.id
        while True:
            result_status = client.search_status(search_id=search_id)
            status = result_status[0].status
            if status != "Running":
                break
        dict_search_results = client.search_results(search_id=search_id)
        search_results = dict_search_results.results
        total_results = dict_search_results.total
        link = _getResult(search_results, key, message, method)
        buttons = button_build.ButtonMaker()
        buttons.buildbutton("🔎 VIEW", link)
        button = InlineKeyboardMarkup(buttons.build_menu(1))
        if total_results == 0:
            elapsed_time = f"\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}"
            return editMessage(
                f"Nᴏ ʀᴇsᴜʟᴛ ꜰᴏᴜɴᴅ ꜰᴏʀ <i>{key}</i> \nTᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{site.capitalize()}</i> {elapsed_time}",
                message,
            )
        msg = f"<b>Fᴏᴜɴᴅ {min(total_results, TELEGRAPH_LIMIT)}</b> "
        msg += f"<b>Rᴇsᴜʟᴛs(s)) Fᴏʀ <i>{key}</i> \n Tᴏʀʀᴇɴᴛ Sɪᴛᴇ ⇢ <i>{site.capitalize()}</i></b>"
    msg += f"\n⏰ Eʟᴀᴘsᴇᴅ Tɪᴍᴇ ⇢ {get_readable_time(time() - message.date.timestamp())}"
    editMessage(msg, message, button)
    if not method.startswith("api"):
        client.search_delete(search_id=search_id)


def _getResult(search_results, key, message, method):
    telegraph_content = []
    if method == "apirecent":
        msg = "<h4>API Rᴇᴄᴇɴᴛ Rᴇsᴜʟᴛ(s)</h4>"
    elif method == "apisearch":
        msg = f"<h4>API Search Rᴇsᴜʟᴛ(s) For {key} </h4>"
    elif method == "apitrend":
        msg = "<h4>API Tʀᴇɴᴅɪɴɢ Rᴇsᴜʟᴛ(s)</h4>"
    else:
        msg = f"<h4>Pʟᴜɢɪɴs Sᴇᴀʀᴄʜ Rᴇsᴜʟᴛ(s) Fᴏʀ {key} </h4>"
    for index, result in enumerate(search_results, start=1):
        if method.startswith("api"):
            if "name" in result.keys():
                msg += f"<code><a href='{result['url']}'>{escape(result['name'])}</a></code><br>"
            if "torrents" in result.keys():
                for subres in result["torrents"]:
                    msg += f"🎥 Qᴜᴀʟɪᴛʏ ⇢ {subres['quality']} | 💻 Tʏᴘᴇ ⇢ {subres['type']} | 💾 Sɪᴢᴇ ⇢ {subres['size']}<br>"
                    if "torrent" in subres.keys():
                        msg += f"<a href='{subres['torrent']}'>🔗 Dɪʀᴇᴄᴛ Lɪɴᴋ</a><br>"
                    elif "magnet" in subres.keys():
                        msg += f"💘 Sʜᴀʀᴇ Mᴀɢɴᴇᴛ ᴛᴏ <a href='http://t.me/share/url?url={subres['magnet']}'>Tᴇʟᴇɢʀᴀᴍ</a><br>"
                msg += "<br>"
            else:
                msg += f"💾 Sɪᴢᴇ ⇢ {result['size']}<br>"
                try:
                    msg += f"💿 Sᴇᴇᴅᴇʀs ⇢ {result['seeders']} | 🧲 Lᴇᴇᴄʜᴇʀs ⇢ {result['leechers']}<br>"
                except Exception:
                    pass
                if "torrent" in result.keys():
                    msg += f"<a href='{result['torrent']}'>🔗 Dɪʀᴇᴄᴛ Lɪɴᴋ</a><br><br>"
                elif "magnet" in result.keys():
                    msg += f"💘 Sʜᴀʀᴇ Mᴀɢɴᴇᴛ ᴛᴏ <a href='http://t.me/share/url?url={quote(result['magnet'])}'>Tᴇʟᴇɢʀᴀᴍ</a><br><br>"
        else:
            msg += f"<a href='{result.descrLink}'>{escape(result.fileName)}</a><br>"
            msg += f"💾 Sɪᴢᴇ ⇢ {get_readable_file_size(result.fileSize)}<br>"
            msg += (
                f"💿 Sᴇᴇᴅᴇʀs ⇢ {result.nbSeeders} | 🧲 Lᴇᴇᴄʜᴇʀs ⇢ {result.nbLeechers}<br>"
            )
            link = result.fileUrl
            if link.startswith("magnet:"):
                msg += f"<b>💘 Sʜᴀʀᴇ Mᴀɢɴᴇᴛ ᴛᴏ</b> <a href='http://t.me/share/url?url={quote(link)}'>Tᴇʟᴇɢʀᴀᴍ</a><br><br>"
            else:
                msg += f"<b>💘 Sʜᴀʀᴇ Uʀʟ ᴛᴏ</b> <a href='http://t.me/share/url?url={link}'>Tᴇʟᴇɢʀᴀᴍ</a><br><br>"

        if len(msg.encode("utf-8")) > 39000:
            telegraph_content.append(msg)
            msg = ""

        if index == TELEGRAPH_LIMIT:
            break

    if msg != "":
        telegraph_content.append(msg)

    editMessage(f"📇 Cʀᴇᴀᴛɪɴɢ {len(telegraph_content)} 📑 Tᴇʟᴇɢʀᴀᴘʜ Pᴀɢᴇs.", message)
    path = [
        telegraph.create_page(
            title="👿 Dᴇᴠɪʟ Mɪʀʀᴏʀ Bᴏᴛ Tᴏʀʀᴇɴᴛ Sᴇᴀʀᴄʜ", content=content
        )["path"]
        for content in telegraph_content
    ]
    sleep(0.5)
    if len(path) > 1:
        editMessage(
            f"📝 Eᴅɪᴛɪɴɢ {len(telegraph_content)} 📑 Tᴇʟᴇɢʀᴀᴘʜ Pᴀɢᴇs.",
            message,
        )
        telegraph.edit_telegraph(path, telegraph_content)
    return f"https://telegra.ph/{path[0]}"


def _api_buttons(user_id, method):
    buttons = button_build.ButtonMaker()
    for data, name in SITES.items():
        buttons.sbutton(name, f"torser {user_id} {data} {method}")
    buttons.sbutton("Cᴀɴᴄᴇʟ", f"torser {user_id} cancel")
    return InlineKeyboardMarkup(buttons.build_menu(2))


def _plugin_buttons(user_id):
    buttons = button_build.ButtonMaker()
    if not PLUGINS:
        qbclient = get_client()
        pl = qbclient.search_plugins()
        for name in pl:
            PLUGINS.append(name["name"])
        qbclient.auth_log_out()
    for siteName in PLUGINS:
        buttons.sbutton(siteName.capitalize(), f"torser {user_id} {siteName} plugin")
    buttons.sbutton("Aʟʟ", f"torser {user_id} all plugin")
    buttons.sbutton("Cᴀɴᴄᴇʟ", f"torser {user_id} cancel")
    return InlineKeyboardMarkup(buttons.build_menu(2))


torser_handler = CommandHandler(
    BotCommands.SearchCommand,
    torser,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
torserbut_handler = CallbackQueryHandler(torserbut, pattern="torser", run_async=True)

dispatcher.add_handler(torser_handler)
dispatcher.add_handler(torserbut_handler)
