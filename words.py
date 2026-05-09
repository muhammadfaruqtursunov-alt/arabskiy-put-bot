import json
import random
from config import WORDS_PATH, WORDS_PER_LESSON

_data = None
_lesson_cache = {}

def _load():
    global _data
    if _data is None:
        with open(WORDS_PATH, encoding="utf-8") as f:
            _data = json.load(f)
    return _data

def get_lesson_words(volume: int, lesson: int) -> list[dict]:
    key = (volume, lesson)
    if key in _lesson_cache:
        return _lesson_cache[key]
    
    data = _load()
    for vol in data["volumes"]:
        if vol["volume"] == volume:
            for les in vol["lessons"]:
                if les["lesson"] == lesson:
                    _lesson_cache[key] = les["words"]
                    return les["words"]
    return []

def get_lesson_meta(volume: int, lesson: int) -> dict:
    data = _load()
    for vol in data["volumes"]:
        if vol["volume"] == volume:
            for les in vol["lessons"]:
                if les["lesson"] == lesson:
                    return {
                        "theme_ar": les["theme_ar"],
                        "theme_tj": les["theme_tj"],
                        "theme_ru": les["theme_ru"],
                    }
    return {}

def get_words_by_ids(word_ids: list[int]) -> list[dict]:
    data = _load()
    result = {}
    for vol in data["volumes"]:
        for les in vol["lessons"]:
            for w in les["words"]:
                if w["id"] in word_ids:
                    result[w["id"]] = w
    return [result[wid] for wid in word_ids if wid in result]

def get_all_week_words(volume: int, lessons: list[int]) -> list[dict]:
    all_words = []
    for lesson in lessons:
        all_words.extend(get_lesson_words(volume, lesson))
    return all_words

def make_visual_choices(correct: dict, all_words: list[dict], lang: str) -> list[str]:
    wrong_pool = [w for w in all_words if w["id"] != correct["id"]]
    wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
    choices = [correct] + wrong
    random.shuffle(choices)

    def label(w):
        if lang == "ru":
            return w["ru"]
        elif lang == "tj":
            return w["tj"]
        else:
            return f"{w['tj']} / {w['ru']}"

    return [label(w) for w in choices], label(correct)

def normalize(text: str) -> str:
    return text.strip().lower()
