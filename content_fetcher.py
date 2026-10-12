"""
منابع محتوای پزشکی معتبر
- تخصصی: NEJM, Lancet, JAMA, BMJ, Nature Medicine, CDC EID, PubMed
- عمومی: WHO, Mayo Clinic, MedlinePlus, NIH
"""
import logging
import time
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# منابع تخصصی (برای پزشکان و دانشجویان پزشکی)
# ═══════════════════════════════════════════════════════
SPECIALIZED_FEEDS = {
    "NEJM": "https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm",
    "The Lancet": "https://www.thelancet.com/rssfeed/lancet_current.xml",
    "JAMA": "https://jamanetwork.com/rss/site_3/67.xml",
    "BMJ": "https://www.bmj.com/rss/recent.xml",
    "Nature Medicine": "https://www.nature.com/nm.rss",
    "CDC EID": "https://wwwnc.cdc.gov/eid/rss/current.xml",
    "PubMed Oncology": "https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=cancer+therapy&format=rss",
    "PubMed HIV": "https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=HIV+AIDS+treatment&format=rss",
    "PubMed Infectious": "https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=infectious+disease&format=rss",
}


# ═══════════════════════════════════════════════════════
# منابع عمومی (برای عموم مردم)
# ═══════════════════════════════════════════════════════
GENERAL_FEEDS = {
    "WHO": "https://www.who.int/rss-feeds/news-english.xml",
    "Mayo Clinic": "https://newsnetwork.mayoclinic.org/feed/",
    "MedlinePlus": "https://medlineplus.gov/feeds/news_en.xml",
    "NIH News": "https://www.nih.gov/news-events/news-releases/feed.xml",
}


def _clean_html(raw):
    """حذف تگ‌های HTML از متن"""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _is_recent(entry, hours=48):
    """چک کنه مقاله توی بازه زمانی مشخص منتشر شده"""
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
            return datetime.now() - published < timedelta(hours=hours)
    except Exception:
        pass
    return True


def _fetch_feed(source_name, url, max_items=3):
    """خوندن یک RSS Feed"""
    articles = []
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            log.warning(f"⚠️ {source_name}: خالی")
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

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:1500],
                "link": link,
                "published": published,
                "category": "specialized" if source_name in SPECIALIZED_FEEDS else "general",
            })

        log.info(f"✅ {source_name}: {len(articles)} مقاله")
    except Exception as e:
        log.error(f"❌ {source_name}: {str(e)[:80]}")

    return articles


def fetch_all_articles():
    """دریافت مقالات از همه منابع"""
    log.info("📚 شروع دریافت مقالات از منابع پزشکی...")
    all_articles = []

    log.info("\n🔬 منابع تخصصی:")
    for name, url in SPECIALIZED_FEEDS.items():
        articles = _fetch_feed(name, url, max_items=3)
        all_articles.extend(articles)
        time.sleep(0.5)

    log.info("\n🩺 منابع عمومی:")
    for name, url in GENERAL_FEEDS.items():
        articles = _fetch_feed(name, url, max_items=3)
        all_articles.extend(articles)
        time.sleep(0.5)

    log.info(f"\n🎯 مجموع: {len(all_articles)} مقاله")
    return all_articles


def fetch_article_full_text(url, max_chars=3000):
    """دریافت متن کامل مقاله از لینک (اختیاری)"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MedicalBot/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        article_body = (
            soup.find("article") or
            soup.find("div", class_="article-body") or
            soup.find("div", class_="content") or
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
        log.warning(f"⚠️ خطا در دریافت متن کامل: {str(e)[:80]}")
        return ""


if __name__ == "__main__":
    articles = fetch_all_articles()
    print(f"\n📊 {len(articles)} مقاله دریافت شد\n")
    for a in articles[:5]:
        print(f"[{a['source']}] {a['title'][:80]}")
        print(f"   🔗 {a['link']}\n")