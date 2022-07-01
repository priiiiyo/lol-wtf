from signal import signal, SIGINT
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
import requests
from sys import executable
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler

from bot import bot, dispatcher, updater, botStartTime, IGNORE_PENDING_REQUESTS, LOGGER, HEROKU_API_KEY, HEROKU_APP_NAME, bot, app, dispatcher, updater, botStartTime, \
    IGNORE_PENDING_REQUESTS, IS_VPS, PORT, INCOMPLETE_TASK_NOTIFIER, DB_URI, alive, app, main_loop
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from bot.modules.wayback import getRandomUserAgent
from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, delete, count, leech_settings, search, rss

try: import heroku3
except ModuleNotFoundError: srun("pip install heroku3", capture_output=False, shell=True)
try: import heroku3
except Exception as f:
    LOGGER.warning("heroku3 cannot imported. add to your deployer requirements.txt file.")
    LOGGER.warning(f)
    HEROKU_APP_NAME = None
    HEROKU_API_KEY = None


def getHerokuDetails(h_api_key, h_app_name):
    try: import heroku3
    except ModuleNotFoundError: run("pip install heroku3", capture_output=False, shell=True)
    try: import heroku3
    except Exception as f:
        LOGGER.warning("heroku3 cannot imported. add to your deployer requirements.txt file.")
        LOGGER.warning(f)
        return None
    if (not h_api_key) or (not h_app_name): return None
    try:
        heroku_api = "https://api.heroku.com"
        Heroku = heroku3.from_key(h_api_key)
        app = Heroku.app(h_app_name)
        useragent = getRandomUserAgent()
        user_id = Heroku.account().id
        headers = {
            "User-Agent": useragent,
            "Authorization": f"Bearer {h_api_key}",
            "Accept": "application/vnd.heroku+json; version=3.account-quotas",
        }
        path = "/accounts/" + user_id + "/actions/get-quota"
        session = requests.Session()
        result = (session.get(heroku_api + path, headers=headers)).json()
        abc = ""
        account_quota = result["account_quota"]
        quota_used = result["quota_used"]
        quota_remain = account_quota - quota_used
        abc += f"\n<b>Total Dyno : </b>{get_readable_time(account_quota)}"
        abc += f"\n<b>Used : </b>{get_readable_time(quota_used)} | "
        abc += f"<b>Left : </b>{get_readable_time(quota_remain)}\n"
        return abc
    except Exception as g:
        LOGGER.error(g)
        return None

def stats(update, context):
    if ospath.exists('.git'):
        last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd <b>From</b> %cr'"], shell=True).decode()
    else:
        last_commit = 'No UPSTREAM_REPO'
    currentTime = get_readable_time(time() - botStartTime)
    botVersion = check_output(["git log -1 --date=format:v%y.%m%d.%H%M --pretty=format:%cd"], shell=True).decode()
    osUptime = get_readable_time(time() - boot_time())
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    swap_t = get_readable_file_size(swap.total)
    memory = virtual_memory()
    mem_p = memory.percent
    mem_t = get_readable_file_size(memory.total)
    mem_a = get_readable_file_size(memory.available)
    mem_u = get_readable_file_size(memory.used)
    stats = f'<b>Commit Date:</b> {last_commit}\n\n'\
            f'<b>Bot Version:</b> {botVersion}\n'\
            f'<b>Bot Uptime:</b> {currentTime}\n'\
            f'<b>OS Uptime:</b> {osUptime}\n\n'\
            f'<b>Total Disk Space:</b> {total}\n'\
            f'<b>Used:</b> {used} | <b>Free:</b> {free}\n\n'\
            f'<b>Upload:</b> {sent}\n'\
            f'<b>Download:</b> {recv}\n\n'\
            f'<b>CPU:</b> {cpuUsage}%\n'\
            f'<b>RAM:</b> {mem_p}%\n'\
            f'<b>DISK:</b> {disk}%\n\n'\
            f'<b>Physical Cores:</b> {p_core}\n'\
            f'<b>Total Cores:</b> {t_core}\n\n'\
            f'<b>SWAP:</b> {swap_t} | <b>Used:</b> {swap_p}%\n'\
            f'<b>Memory Total:</b> {mem_t}\n'\
            f'<b>Memory Free:</b> {mem_a}\n'\
            f'<b>Memory Used:</b> {mem_u}\n'
    sendMessage(stats, context.bot, update.message)

def hstats(update, context):
    currentTime = get_readable_time(time() - botStartTime)
    hstats = f'<b>Heroku App Name :</b> {HEROKU_APP_NAME}\n'\
             f'<b>App Uptime :</b> {currentTime}\n'
    heroku = getHerokuDetails(HEROKU_API_KEY, HEROKU_APP_NAME)
    if heroku: hstats += heroku
    sendMessage(hstats, context.bot, update.message)

def start(update, context):
    buttons = ButtonMaker()
    buttons.buildbutton("Mirror Group", "https://t.me/dipeshmirror")
    buttons.buildbutton("Channel", "https://t.me/dipeshmirror")
    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        start_string = f'''
This bot can mirror all your links to Google Drive!
Join our Mirror Group To Acces BoT!
'''
        sendMarkup(start_string, context.bot, update.message, reply_markup)
    else:
        sendMarkup('Not Authorized user, Join our Mirror Group to Access BoTs!', context.bot, update.message, reply_markup)

def restart(update, context):
    cmd = update.effective_message.text.split(' ', 1)
    dynoRestart = False
    dynoKill = False
    if len(cmd) == 2:
        dynoRestart = (cmd[1].lower()).startswith('d')
        dynoKill = (cmd[1].lower()).startswith('k')
    if (not HEROKU_API_KEY) or (not HEROKU_APP_NAME):
        LOGGER.info("If you want Heroku features, fill HEROKU_APP_NAME HEROKU_API_KEY vars.")
        dynoRestart = False
        dynoKill = False
    if dynoRestart:
        LOGGER.info("Dyno Restarting.")
        restart_message = sendMessage("<b>Code Verified~#.\nInitializing force restart...</b>", context.bot, update.message)
        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.app(HEROKU_APP_NAME)
        app.restart()
    elif dynoKill:
        LOGGER.info("Killing Dyno. MUHAHAHA")
        sendMessage("Killed Dyno.", context.bot, update)
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.app(HEROKU_APP_NAME)
        proclist = app.process_formation()
        for po in proclist:
            app.process_formation()[po.type].scale(0)
    else:
        LOGGER.info("Normally Restarting.")
        restart_message = sendMessage("Normally Restarting.", context.bot, update)
        if Interval:
            Interval[0].cancel()
        alive.kill()
        procs = psprocess(web.pid)
        for proc in procs.children(recursive=True):
            proc.kill()
        procs.kill()
        clean_all()
        srun(["python3", "update.py"])
        nox.kill()
        a2cproc = psprocess(a2c.pid)
        for proc in a2cproc.children(recursive=True):
            proc.kill()
        a2cproc.kill()
        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
        osexecl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update.message)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)


help_string_telegraph = f'''<br>
#Mirror_Commands
<br><br>
<b>/{BotCommands.HelpCommand}</b>: To get this message
<br><br>
<b>/{BotCommands.MirrorCommand}</b> [download_url][magnet_link]: Start mirroring to Google Drive. Send <b>/{BotCommands.MirrorCommand}</b> for more help
<br><br>
<b>/{BotCommands.ZipMirrorCommand}</b> [download_url][magnet_link]: Start mirroring and upload the file/folder compressed with zip extension
<br><br>
<b>/{BotCommands.UnzipMirrorCommand}</b> [download_url][magnet_link]: Start mirroring and upload the file/folder extracted from any archive extension
<br><br>
<b>/{BotCommands.QbMirrorCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start Mirroring using qBittorrent, Use <b>/{BotCommands.QbMirrorCommand} s</b> to select files before downloading
<br><br>
<b>/{BotCommands.QbZipMirrorCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension
<br><br>
<b>/{BotCommands.QbUnzipMirrorCommand}</b> [magnet_link][torrent_file][torrent_file_url]: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension
<br><br>
<b>/{BotCommands.WatchCommand}</b> [yt-dlp supported link]: Mirror yt-dlp supported link. Send <b>/{BotCommands.WatchCommand}</b> for more help
<br><br>
<b>/{BotCommands.ZipWatchCommand}</b> [yt-dlp supported link]: Mirror yt-dlp supported link as zip
<br><br>
#Other_Commands
<br><br>
<b>/{BotCommands.CloneCommand}</b> [drive_url][gdtot_url]: Copy file/folder to Google Drive
<br><br>
<b>/{BotCommands.ListCommand}</b> [query]: Search in Google Drive(s)
<br><br>
<b>/{BotCommands.SearchCommand}</b> [query]: Search for torrents with API
<br>sites: <code>rarbg, 1337x, yts, etzv, tgx, torlock, piratebay, nyaasi, ettv</code><br><br>
<br><br>
<b>/{BotCommands.CancelMirror}</b>: Reply to the message by which the download was initiated and that download will be cancelled
<br><br>
<b>/{BotCommands.CancelAllCommand}</b>: Cancel all downloading tasks
<br><br>
<b>/{BotCommands.StatusCommand}</b>: Shows a status of all the downloads
<br><br>
<b>/{BotCommands.StatsCommand}</b>: Show Stats of the machine the bot is hosted on
'''

help = telegraph.create_page(
        title='Bot Commands qbit-Mirrors',
        content=help_string_telegraph,
    )["path"]

help_string = f'''
💡 Click On View To See Help.
'''
def bot_help(update, context):
    button = ButtonMaker()
    button.buildbutton("View💻", f"https://telegra.ph/{help}")
    reply_markup = InlineKeyboardMarkup(button.build_menu(1))
    sendMarkup(help_string, context.bot, update.message, reply_markup)

def main():
    start_cleanup()
    if INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
        notifier_dict = DbManger().get_incomplete_tasks()
        if notifier_dict:
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = 'Restarted successfully!'
                else:
                    msg = 'Bot Restarted!'
                for tag, links in data.items():
                     msg += f"\n\n{tag}: "
                     for index, link in enumerate(links, start=1):
                         msg += f" <a href='{link}'>{index}</a> |"
                         if len(msg.encode()) > 4000:
                             if 'Restarted successfully!' in msg and cid == chat_id:
                                 bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                                 osremove(".restartmsg")
                             else:
                                 bot.sendMessage(cid, msg, 'HTML')
                             msg = ''
                if 'Restarted successfully!' in msg and cid == chat_id:
                     bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                     osremove(".restartmsg")
                else:
                    bot.sendMessage(cid, msg, 'HTML')

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text("Restarted successfully!", chat_id, msg_id)
        osremove(".restartmsg")

    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                  bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    hstats_handler = CommandHandler(BotCommands.HStatsCommand,
                                   hstats, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(hstats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

main()
app.start()

main_loop.run_forever()
