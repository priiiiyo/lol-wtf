import math
from logging import error as log_error
from threading import Thread

import heroku3
import requests
from telegram import update
from telegram.ext import CommandHandler

from bot import HEROKU_API_KEY, HEROKU_APP_NAME, dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage


def dyno_usage(update, context):
    try:
        heroku_api = "https://api.heroku.com"
        if HEROKU_API_KEY is not None and HEROKU_APP_NAME is not None:
            Heroku = heroku3.from_key(HEROKU_API_KEY)
            app = Heroku.app(HEROKU_APP_NAME)
        else:
            reply_message = sendMessage(
                "Please insert your HEROKU_APP_NAME and HEROKU_API_KEY in Vars",
                context.bot,
                update.message,
            )
            Thread(
                target=auto_delete_message,
                args=(context.bot, update.message, reply_message),
            ).start()
            return reply_message
        useragent = (
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/81.0.4044.117 Mobile Safari/537.36"
        )
        user_id = Heroku.account().id
        headers = {
            "User-Agent": useragent,
            "Authorization": f"Bearer {HEROKU_API_KEY}",
            "Accept": "application/vnd.heroku+json; version=3.account-quotas",
        }
        path = f"/accounts/{user_id}/actions/get-quota"
        session = requests.Session()
        with session as ses:
            with ses.get(heroku_api + path, headers=headers) as r:
                result = r.json()
                """Account Quota."""
                quota = result["account_quota"]
                quota_used = result["quota_used"]
                quota_remain = quota - quota_used
                quota_percent = math.floor(quota_remain / quota * 100)
                minutes_remain = quota_remain / 60
                hours = math.floor(minutes_remain / 60)
                minutes = math.floor(minutes_remain % 60)
                day = math.floor(hours / 24)

                """App Quota."""
                Apps = result["apps"]
                for apps in Apps:
                    if apps.get("app_uuid") == app.id:
                        AppQuotaUsed = apps.get("quota_used") / 60
                        AppPercent = math.floor(apps.get("quota_used") * 100 / quota)
                        break
                else:
                    AppQuotaUsed = 0
                    AppPercent = 0

                AppHours = math.floor(AppQuotaUsed / 60)
                AppMinutes = math.floor(AppQuotaUsed % 60)

                reply_message = sendMessage(
                    f" 𝗗𝘆𝗻𝗼 𝗨𝘀𝗮𝗴𝗲 \n\n<code>𝗗𝘆𝗻𝗼 𝗨𝘀𝗮𝗴𝗲 ⇢ {app.name}</code>\n"
                    f"🕐 <code>{AppHours}</code> 𝗛𝗼𝘂𝗿𝘀 <code>{AppMinutes}</code> 𝗠𝗶𝗻𝘂𝘁𝗲𝘀\n𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 ⇢ {AppPercent}%\n\n"
                    "⚠️ 𝗗𝘆𝗻𝗼 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 ⚠️\n"
                    f"🕐 <code>{hours}</code> 𝗛𝗼𝘂𝗿𝘀 <code>{minutes}</code> 𝗠𝗶𝗻𝘂𝘁𝗲𝘀\n𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 ⇢ {quota_percent}%\n\n"
                    "❌ 𝗘𝘀𝘁𝗶𝗺𝗮𝘁𝗲𝗱 𝗘𝘅𝗽𝗶𝗿𝗲𝗱 ❌\n"
                    f"📅 <code>{day}</code> 𝗗𝗮𝘆𝘀",
                    context.bot,
                    update.message,
                )
                Thread(
                    target=auto_delete_message,
                    args=(context.bot, update.message, reply_message),
                ).start()
                return reply_message
    except Exception as g:
        log_error(str(g))
        reply_message = sendMessage(f"{str(g)}", context.bot, update.message)
        Thread(
            target=auto_delete_message,
            args=(context.bot, update.message, reply_message),
        ).start()
        return reply_message


dyno_usage_handler = CommandHandler(
    command=BotCommands.UsageCommand,
    callback=dyno_usage,
    filters=CustomFilters.owner_filter,
    run_async=True,
)

dispatcher.add_handler(dyno_usage_handler)
