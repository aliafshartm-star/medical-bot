import logging
import time
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)


PERSIAN_FEEDS = {
    "سلامت نیوز": "https://www.salamatnews.com/rss",
    "بهداشت نیوز": "https://behdashtnews.ir/feed/",
    "طبنا": "https://www.tabnak.ir/fa/rss/40",
    "شفاآنلاین": "https://shafaonline.ir/fa/rss",
    "سیناپرس سلامت": "https://sinapress.ir/feed",
    "مهر سلامت": "https://www.mehrnews.com/rss",
    "ایسنا سلامت": "https://www.isna.ir/rss",
}

MEDICAL_KEYWORDS = [
    "سلامت", "پزشک", "بیماری", "درمان", "دارو", "بیمار",
    "سرطان", "دیابت", "قلب", "فشار خون", "ویروس", "واکسن",
    "عفونت", "میکروب", "آنتی بیوتیک", "بیمارستان", "جراحی",
    "تغذیه", "ویتامین", "مکمل", "چاقی", "اضافه وزن",
    "روان", "افسردگی", "اضطراب", "خواب", "مغز", "اعصاب",
    "کبد", "کلیه", "ریه", "معده", "روده", "خون", "تومور",
    "ایدز", "هپاتیت", "کرونا", "آنفولانزا", "آلرژی",
    "بارداری", "زایمان", "ناباروری", "نوزاد",
    "پوکی استخوان", "مفاصل", "آرتروز", "پوست",
    "چشم", "گوش", "دندان", "لثه", "تیروئید", "هورمون",
    "ژنتیک", "سلول", "آزمایش", "تشخیص",
    "علائم", "نشانه", "پیشگیری", "مراقبت",
    "سازمان بهداشت", "WHO", "پاندمی", "اپیدمی",
    "پژوهشگران", "محققان", "مطالعه",
]


def _clean_html(raw):
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _extract_image(entry, summary_html):
    """استخراج عکس از RSS"""
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            url = media.get("url")
            if url and any(url.lower().split("?")[0].endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                return url

    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            url = thumb.get("url")
            if url:
                return url

    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href") or enc.get("url")

    if summary_html:
        soup = BeautifulSoup(summary_html, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    return None


def _is_medical(text):
    if not text:
        return False
    for keyword in MEDICAL_KEYWORDS:
        if keyword in text:
            return True
    return False


def _is_recent(entry, hours=96):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
            return datetime.now() - published < timedelta(hours=hours)
    except Exception:
        pass
    return True


def _fetch_feed(source_name, url, max_items=5):
    articles = []
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            log.warning("⚠️ " + source_name + ": خالی")
            return articles

        count = 0
        for entry in feed.entries[:25]:
            if count >= max_items:
                break

            if not _is_recent(entry, hours=96):
                continue

            title = _clean_html(entry.get("title", "")).strip()
            summary_html = entry.get("summary", entry.get("description", ""))
            summary = _clean_html(summary_html).strip()
            link = entry.get("link", "").strip()
            published = entry.get("published", "").strip()

            if not title or not link:
                continue

            if not (_is_medical(title) or _is_medical(summary)):
                continue

            image_url = _extract_image(entry, summary_html)

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:1500],
                "link": link,
                "published": published,
                "image_url": image_url,
            })
            count += 1

        log.info("✅ " + source_name + ": " + str(len(articles)) + " خبر")
    except Exception as e:
        log.error("❌ " + source_name + ": " + str(e)[:80])

    return articles


def fetch_all_articles():
    log.info("📚 شروع دریافت اخبار پزشکی...")
    all_articles = []

    for name, url in PERSIAN_FEEDS.items():
        articles = _fetch_feed(name, url, max_items=5)
        all_articles.extend(articles)
        time.sleep(0.3)

    log.info("\n🎯 مجموع: " + str(len(all_articles)) + " خبر")
    return all_articles


if __name__ == "__main__":
    articles = fetch_all_articles()
    print("\n📊 " + str(len(articles)) + " خبر")
    for a in articles[:5]:
        print("[" + a['source'] + "] " + a['title'][:80])
        print("   🖼 " + str(a.get('image_url'))[:80])
        print("   🔗 " + a['link'] + "\n")