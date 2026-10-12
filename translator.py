"""
ترجمه مقالات به فارسی با retry و fallback
- اول: Google Translate
- دوم: MyMemory Translator (اگه گوگل رد کرد)
"""
import logging
import time
import hashlib
import os
import json

from deep_translator import GoogleTranslator, MyMemoryTranslator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# کش ترجمه (جلوگیری از ترجمه تکراری)
# ═══════════════════════════════════════════════════════
CACHE_FILE = os.path.join(os.path.dirname(__file__), "translation_cache.json")
_translation_cache = {}


def _load_cache():
    global _translation_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _translation_cache = json.load(f)
            log.info(f"📦 {len(_translation_cache)} ترجمه در کش")
    except Exception:
        _translation_cache = {}


def _save_cache():
    try:
        # فقط ۲۰۰۰ ترجمه آخر
        if len(_translation_cache) > 2000:
            items = list(_translation_cache.items())[-2000:]
            _translation_cache = dict(items)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_translation_cache, f, ensure_ascii=False)
    except Exception as e:
        log.warning(f"⚠️ خطا در ذخیره کش: {e}")


def _cache_key(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _split_text(text, max_len=4500):
    """تقسیم متن طولانی به تکه‌های کوچک‌تر"""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
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


def _translate_google(text):
    """ترجمه با Google Translate"""
    translator = GoogleTranslator(source="en", target="fa")
    chunks = _split_text(text, max_len=4500)
    translated_parts = []
    for chunk in chunks:
        result = translator.translate(chunk)
        translated_parts.append(result or chunk)
        time.sleep(1.0)  # مهم: فاصله بین درخواست‌ها
    return "\n".join(translated_parts)


def _translate_mymemory(text):
    """ترجمه با MyMemory (رایگان، بدون نیاز به API)"""
    translator = MyMemoryTranslator(source="en-US", target="fa-IR")
    chunks = _split_text(text, max_len=450)
    translated_parts = []
    for chunk in chunks:
        try:
            result = translator.translate(chunk)
            translated_parts.append(result or chunk)
        except Exception:
            translated_parts.append(chunk)
        time.sleep(1.5)
    return "\n".join(translated_parts)


def translate_to_fa(text, max_retries=3):
    """ترجمه با retry و fallback"""
    if not text or not text.strip():
        return ""

    text = text.strip()

    # چک کش
    key = _cache_key(text)
    if key in _translation_cache:
        return _translation_cache[key]

    # تلاش اول: Google
    for attempt in range(1, max_retries + 1):
        try:
            result = _translate_google(text)
            if result and result.strip():
                _translation_cache[key] = result
                return result
        except Exception as e:
            err = str(e)[:80]
            log.warning(f"⚠️ Google ({attempt}/{max_retries}): {err}")
            # backoff: ۵، ۱۰، ۲۰ ثانیه
            wait = 5 * (2 ** (attempt - 1))
            time.sleep(wait)

    # تلاش دوم: MyMemory
    log.info("🔄 Google کار نکرد، تلاش با MyMemory...")
    try:
        result = _translate_mymemory(text)
        if result and result.strip():
            _translation_cache[key] = result
            log.info("✅ ترجمه با MyMemory موفق")
            return result
    except Exception as e:
        log.error(f"❌ MyMemory هم کار نکرد: {str(e)[:80]}")

    # اگه هیچی نشد، متن اصلی برگرده
    log.warning("⚠️ ترجمه ناموفق، متن اصلی برگردانده شد")
    return text


def translate_title(title):
    """ترجمه عنوان"""
    if not title:
        return ""
    return translate_to_fa(title)


def translate_summary(summary):
    """ترجمه خلاصه (فقط ۱۰۰۰ کاراکتر اول برای صرفه‌جویی)"""
    if not summary:
        return ""
    return translate_to_fa(summary[:1500])


# بارگذاری کش در شروع
_load_cache()


if __name__ == "__main__":
    test = "New study shows that hypertension treatment reduces cardiovascular risk."
    print(f"Original: {test}")
    print(f"Translated: {translate_to_fa(test)}")
    _save_cache()