import logging
import time
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)


# RSSهای تخصصی سلامت
PERSIAN_FEEDS = {
    "سلامت نیوز": "https://www.salamatnews.com/rss",
    "بهداشت نیوز": "https://behdashtnews.ir/feed/",
    "طبنا": "https://www.tabnak.ir/fa/rss/40",
    "شفاآنلاین": "https://shafaonline.ir/fa/rss",
    "پزشکان بدون مرز": "https://www.msf.org/rss.xml",
    "سیناپرس سلامت": "https://sinapress.ir/feed",
}

# کلمات کلیدی پزشکی (فیلتر)
MEDICAL_KEYWORDS = [
    "سلامت", "پزشک", "بیماری", "درمان", "دارو", "بیمار",
    "سرطان", "دیابت", "قلب", "فشار خون", "ویروس", "واکسن",
    "عفونت", "میکروب", "آنتی بیوتیک", "بیمارستان", "جراحی",
    "تغذیه", "ویتامین", "مکمل", "ورزش", "چاقی", "اضافه وزن",
    "روان", "افسردگی", "اضطراب", "خواب", "مغز", "اعصاب",
    "کبد", "کلیه", "ریه", "معده", "روده", "خون", "تومور",
    "ایدز", "هپاتیت", "کرونا", "آنفولانزا", "آلرژی",
    "بارداری", "زایمان", "ناباروری", "کودک", "نوزاد",
    "پوکی استخوان", "مفاصل", "آرتروز", "پوست", "مو",
    "چشم", "گوش", "دندان", "لثه", "تیروئید", "هورمون",
    "ژنتیک", "DNA", "سلول", "بافت", "آزمایش", "تشخیص",
    "علائم", "نشانه", "پیشگیری", "درمان", "مراقبت",
    "سازمان بهداشت", "WHO", "پاندمی", "اپیدمی",
]


def _clean_html(raw):
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _is_medical(text):
    """چک کنه متن شامل کلمات کلیدی پزشکی هست"""
    if not text:
        return False
    text_lower = text
    for keyword in MEDICAL_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def _is_recent(entry, hours=72):
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

        medical_count = 0
        for entry in feed.entries[:20]:  # ۲۰ تا چک کن، ۵ تا بردار
            if medical_count >= max_items:
                break

            if not _is_recent(entry, hours=96):
                continue

            title = _clean_html(entry.get("title", "")).strip()
            summary = _clean_html(
                entry.get("summary", entry.get("description", ""))
            ).strip()
            link = entry.get("link", "").strip()
            published = entry.get("published", "").strip()

            if not title or not link:
                continue

            # فیلتر پزشکی
            if not (_is_medical(title) or _is_medical(summary)):
                continue

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:2000],
                "link": link,
                "published": published,
                "category": "medical",
            })
            medical_count += 1

        log.info("✅ " + source_name + ": " + str(len(articles)) + " مقاله پزشکی")
    except Exception as e:
        log.error("❌ " + source_name + ": " + str(e)[:80])

    return articles


def fetch_all_articles():
    log.info("📚 شروع دریافت مقالات پزشکی فارسی...")
    all_articles = []

    for name, url in PERSIAN_FEEDS.items():
        articles = _fetch_feed(name, url, max_items=5)
        all_articles.extend(articles)
        time.sleep(0.3)

    log.info("\n🎯 مجموع: " + str(len(all_articles)) + " مقاله پزشکی")
    return all_articles


def fetch_article_full_text(url, max_chars=5000):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MedicalBot/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "noscript"]):
            tag.decompose()

        # تلاش برای پیدا کردن متن اصلی (ساختارهای مختلف خبرگزاری‌ها)
        selectors = [
            {"name": "div", "class_": "item-text"},
            {"name": "div", "class_": "article-body"},
            {"name": "div", "class_": "news-text"},
            {"name": "div", "class_": "body"},
            {"name": "div", "class_": "content"},
            {"name": "div", "class_": "news-text-body"},
            {"name": "div", "class_": "item_body"},
            {"name": "article"},
            {"name": "main"},
        ]

        article_body = None
        for selector in selectors:
            if "class_" in selector:
                article_body = soup.find(selector["name"], class_=selector["class_"])
            else:
                article_body = soup.find(selector["name"])
            if article_body and len(article_body.get_text(strip=True)) > 200:
                break

        if not article_body:
            article_body = soup.body

        if not article_body:
            return ""

        text = article_body.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 20]
        text = "\n".join(lines)

        # حذف خطوط تکراری
        seen_lines = set()
        unique_lines = []
        for line in text.split("\n"):
            if line not in seen_lines:
                seen_lines.add(line)
                unique_lines.append(line)
        text = "\n".join(unique_lines)

        return text[:max_chars]
    except Exception as e:
        log.warning("⚠️ خطا در متن کامل: " + str(e)[:80])
        return ""


if __name__ == "__main__":
    articles = fetch_all_articles()
    print("\n📊 " + str(len(articles)) + " مقاله")
    for a in articles[:5]:
        print("[" + a['source'] + "] " + a['title'][:80])
        print("   🔗 " + a['link'] + "\n")