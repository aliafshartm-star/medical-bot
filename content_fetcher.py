"""
دریافت مقالات از منابع معتبر Open Access
"""
import logging
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import feedparser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# منابع معتبر Open Access
OPEN_ACCESS_FEEDS = {
    "PMC Open Access": "https://www.ncbi.nlm.nih.gov/pmc/tools/rss/",
    "DOAJ": "https://doaj.org/rss/genre,article",
    "medRxiv": "https://connect.medrxiv.org/medrxiv_xml.php",
    "Europe PMC": "https://europepmc.org/rss",
}

def _clean_html(raw):
    """حذف تگ‌های HTML از متن"""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def _is_recent(entry, hours=72):
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
            summary = _clean_html(entry.get("summary", entry.get("description", ""))).strip()
            link = entry.get("link", "").strip()
            published = entry.get("published", "").strip()
            doi = entry.get("dc_identifier", "").strip() # برای دریافت DOI

            if not title or not link:
                continue

            articles.append({
                "source": source_name,
                "title": title,
                "summary": summary[:2000],
                "link": link,
                "published": published,
                "doi": doi,
                "category": "specialized",
            })

        log.info(f"✅ {source_name}: {len(articles)} مقاله")
    except Exception as e:
        log.error(f"❌ {source_name}: {str(e)[:80]}")

    return articles

def fetch_all_articles():
    """دریافت مقالات از همه منابع"""
    log.info("📚 شروع دریافت مقالات از منابع Open Access...")
    all_articles = []

    for name, url in OPEN_ACCESS_FEEDS.items():
        articles = _fetch_feed(name, url, max_items=5)
        all_articles.extend(articles)
        time.sleep(0.5)

    log.info(f"\n🎯 مجموع: {len(all_articles)} مقاله")
    return all_articles

def fetch_article_full_text(url, max_chars=5000):
    """دریافت متن کامل مقاله از لینک"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MedicalBot/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        article_body = soup.find("article") or soup.find("div", class_="article-body") or soup.find("main") or soup.body
        if not article_body:
            return ""

        text = article_body.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)[:max_chars]
    except Exception as e:
        log.warning(f"⚠️ خطا در دریافت متن کامل: {str(e)[:80]}")
        return ""

if __name__ == "__main__":
    articles = fetch_all_articles()
    print(f"\n📊 {len(articles)} مقاله دریافت شد\n")
    for a in articles[:5]:
        print(f"[{a['source']}] {a['title'][:80]}")
        print(f"   🔗 {a['link']}\n")