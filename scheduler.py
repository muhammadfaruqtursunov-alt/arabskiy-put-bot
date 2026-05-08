import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import database as db
from locales import get_reminder_text

scheduler = AsyncIOScheduler()
_bot = None


def setup(bot):
    global _bot
    _bot = bot
    scheduler.add_job(send_reminders, CronTrigger(minute="*"), id="reminders")
    scheduler.start()
    logging.info("Scheduler started.")


async def send_reminders():
    now = datetime.now()
    current_time = f"{now.hour:02d}:{now.minute:02d}"
    weekday = now.weekday()  # 0=Mon, 6=Sun

    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, lang FROM users WHERE reminder_time=?",
            (current_time,)
        ).fetchall()

    for row in rows:
        user_id = row["user_id"]
        ui = row["lang"] if row["lang"] in ("ru", "tj") else "ru"
        text = get_reminder_text(ui, weekday)
        try:
            await _bot.send_message(user_id, text + "\n\n/start_lesson", parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Reminder failed for {user_id}: {e}")
