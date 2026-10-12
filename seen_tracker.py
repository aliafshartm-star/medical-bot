"""
مدیریت حافظه ربات - جلوگیری از ارسال مقالات تکراری
"""
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_articles.json")


def load_seen():
    """خوندن لیست لینک‌های دیده شده"""
    try:
        if not os.path.exists(SEEN_FILE):
            return set()
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("seen_urls", []))
    except Exception as e:
        log.warning(f"⚠️ خطا در خواندن seen_articles: {e}")
        return set()


def save_seen(seen_set):
    """ذخیره لیست لینک‌های دیده شده"""
    try:
        # فقط ۵۰۰۰ لینک آخر رو نگه دار (جلوگیری از بزرگ شدن فایل)
        urls_list = list(seen_set)
        if len(urls_list) > 5000:
            urls_list = urls_list[-5000:]

        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen_urls": urls_list}, f, ensure_ascii=False, indent=2)
        log.info(f"💾 {len(urls_list)} لینک ذخیره شد")
    except Exception as e:
        log.error(f"❌ خطا در ذخیره seen_articles: {e}")


def filter_new(articles, seen_set):
    """فیلتر کردن مقالات جدید"""
    new_articles = []
    for article in articles:
        link = article.get("link", "").strip()
        if link and link not in seen_set:
            new_articles.append(article)
    log.info(f"🆕 {len(new_articles)} مقاله جدید از {len(articles)} مقاله")
    return new_articles


def add_to_seen(seen_set, article):
    """اضافه کردن یک مقاله به لیست دیده شده‌ها"""
    link = article.get("link", "").strip()
    if link:
        seen_set.add(link)
    return seen_set


if __name__ == "__main__":
    # تست محلی
    seen = load_seen()
    print(f"📊 تعداد لینک‌های ذخیره شده: {len(seen)}")

    test_articles = [
        {"link": "https://test1.com", "title": "Article 1"},
        {"link": "https://test2.com", "title": "Article 2"},
    ]

    new = filter_new(test_articles, seen)
    print(f"🆕 مقالات جدید: {len(new)}")

    for a in new:
        add_to_seen(seen, a)
    save_seen(seen)
    print("✅ تست انجام شد")