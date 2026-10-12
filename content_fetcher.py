import logging
import time
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)


PERSIAN_FEEDS = {
    "مهر سلامت": "https://www.mehrnews.com/rss",
    "ایسنا": "https://www.isna.ir/rss",
    "ایرنا": "https://www.irna.ir/rss",
    "سلامت نیوز": "https://www.salamatnews.com/rss",
    "بهداشت نیوز": "https://behdashtnews.ir/feed/",
    "وزارت بهداشت": "https://behdasht.gov.ir/rss",
}


def _clean_html(raw):
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _is_recent(entry, hours=72):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
            return datetime.now() - published < timedelta(hours=hours)
    except Exception:
        pass
    return True


def _fetch_feed(source_name, url, max_items=3):
    articles = []
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            log.warning("⚠️ " + source_name + ": خالی")
            return articles

        for entry in feed.entries[:max_items]:
            if not _is_recent(entry, hours=72):
                continue

            title = _clean_html(entry.get("title", "")).strip()
            summary = _clean_html(
                entry.get("summary", entry.get("description", ""))
            ).strip()
            link = entry.get("link", "").strip()
            published = entry.get("published", "").strip()

            if not title or not link:
                continue

            if len(title) < 10:
                continue

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:2000],
                "link": link,
                "published": published,
                "category": "general",
            })

        log.info("✅ " + source_name + ": " + str(len(articles)) + " مقاله")
    except Exception as e:
        log.error("❌ " + source_name + ": " + str(e)[:80])

    return articles


def fetch_all_articles():
    log.info("📚 شروع دریافت مقالات پزشکی فارسی...")
    all_articles = []

    for name, url in PERSIAN_FEEDS.items():
        articles = _fetch_feed(name, url, max_items=3)
        all_articles.extend(articles)
        time.sleep(0.3)

    log.info("\n🎯 مجموع: " + str(len(all_articles)) + " مقاله")
    return all_articles


def fetch_article_full_text(url, max_chars=5000):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MedicalBot/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        article_body = (
            soup.find("article") or
            soup.find("div", class_="item-text") or
            soup.find("div", class_="article-body") or
            soup.find("div", class_="content") or
            soup.find("div", class_="news-text") or
            soup.find("main") or
            soup.body
        )

        if not article_body:
            return ""

        text = article_body.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

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