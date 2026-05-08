# Арабский путь бот — деплой на Railway

## 1. GitHub
```
git init
git add .
git commit -m "init: Arabic path bot"
git remote add origin https://github.com/YOUR/arabic-bot.git
git push -u origin main
```

## 2. Railway
- New Project → Deploy from GitHub repo
- Add environment variable: `BOT_TOKEN=your_token_here`
- Start command: `python bot.py`

## 3. Команды бота
- `/start` — приветствие
- `/start_lesson` — начать/продолжить урок
- `/settings` — язык + время напоминания
- `/progress` — прогресс

## 4. Структура данных
- `data/words.json` — слова (7 уроков × 10 слов = 70)
- `data/sessions/` — временные файлы еженедельного теста
- `arabic_bot.db` — SQLite база

## 5. Добавить Том 2 / Том 3
В `data/words.json` добавить новый объект в `volumes[]` с `"volume": 2`.
