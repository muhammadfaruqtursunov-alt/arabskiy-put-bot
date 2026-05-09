import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")
DB_PATH = "arabic_bot.db"
WORDS_PATH = "data/words.json"
WORDS_PER_LESSON = 10
WORDS_PER_WEEK = 70
WEEKLY_TEST_COUNT = 25
MAX_FAILURES = 3
