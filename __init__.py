from locales import ru, tj


def t(user_lang: str, key: str, **kwargs) -> str:
    """Get text by key for user's interface language (ru/tj)."""
    # Interface language: if user set 'tj' use tj locale, else ru
    locale = tj.texts if user_lang == "tj" else ru.texts
    text = locale.get(key, ru.texts.get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


def get_fail_text(user_lang: str, index: int) -> str:
    locale = tj.texts if user_lang == "tj" else ru.texts
    texts = locale["fail_texts"]
    return texts[index % len(texts)]


def get_reminder_text(user_lang: str, weekday: int) -> str:
    """weekday: 0=Mon ... 6=Sun"""
    locale = tj.texts if user_lang == "tj" else ru.texts
    texts = locale["reminder_texts"]
    return texts[weekday % len(texts)]
