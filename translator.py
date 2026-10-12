"""
ترجمه مقالات به فارسی با استفاده از LibreTranslate خودمیزبان
"""
import os
import logging
import time
import hashlib
import json
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# آدرس سرور LibreTranslate (از Secrets خونده میشه)
LIBRETRANSLATE_URL = os.environ.get(
    "LIBRETRANSLATE_URL",
    "https://libretranslate-production-8118.up.railway.app"
)

# فایل کش ترجمه
CACHE_FILE = os.path.join(os.path.dirname(__file__), "translation_cache.json")
_cache = {}


def _load_cache():
    global _cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
            log.info(f"📦 {len(_cache)} ترجمه در کش")
    except Exception:
        _cache = {}


def _save_cache():
    try:
        if len(_cache) > 3000:
            items = list(_cache.items())[-3000:]
            _cache.clear()
            _cache.update(dict(items))
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False)
    except Exception as e:
        log.warning(f"⚠️ خطا در ذخیره کش: {e}")


def _cache_key(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _split_text(text, max_len=4500):
    """تقسیم متن طولانی به تکه‌های کوچیک‌تر"""
    if len(text) <= max_len:
        return [text]
    chunks, current = [], ""
    for paragraph in text.split("\n"):
        if len(current) + len(paragraph) + 1 <= max_len:
            current += paragraph + "\n"
        else:
            if current:
                chunks.append(current.strip())
            current = paragraph + "\n"
    if current:
        chunks.append(current.strip())
    return chunks


def _translate_chunk(chunk, max_retries=3):
    """ترجمه یه تکه با retry"""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                f"{LIBRETRANSLATE_URL}/translate",
                json={
                    "q": chunk,
                    "source": "en",
                    "target": "fa",
                    "format": "text"
                },
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("translatedText", "").strip()
            if result:
                return result
        except Exception as e:
            err = str(e)[:100]
            log.warning(f"⚠️ تلاش {attempt}/{max_retries}: {err}")
            time.sleep(3 * attempt)

    log.error("❌ ترجمه این تکه ناموفق بود")
    return chunk


def translate_to_fa(text):
    """ترجمه متن انگلیسی به فارسی"""
    if not text or not text.strip():
        return ""

    text = text.strip()

    # چک کش
    key = _cache_key(text)
    if key in _cache:
        return _cache[key]

    # تقسیم و ترجمه
    chunks = _split_text(text)
    translated_parts = []
    for i, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            log.info(f"   🌐 ترجمه تکه {i}/{len(chunks)}...")
        result = _translate_chunk(chunk)
        translated_parts.append(result)
        if i < len(chunks):
            time.sleep(1)

    final = "\n".join(translated_parts)
    _cache[key] = final
    return final


def translate_title(title):
    if not title:
        return ""
    return translate_to_fa(title)


def translate_summary(summary):
    if not summary:
        return ""
    return translate_to_fa(summary[:2000])


# بارگذاری کش در شروع
_load_cache()


if __name__ == "__main__":
    test = "New study shows that hypertension treatment reduces cardiovascular risk."
    print(f"Original: {test}")
    print(f"Translated: {translate_to_fa(test)}")
    _save_cache()