"""
ViaChart Medical Bot - اجرای اصلی
- دریافت مقالات پزشکی فارسی
- فیلتر مقالات تکراری
- ارسال به کانال تلگرام
"""
import os
import sys
import asyncio
import logging
import random

from content_fetcher import fetch_all_articles, fetch_article_full_text
from seen_tracker import load_seen, save_seen, filter_new, add_to_seen
from telegram_poster import post_article

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════
MAX_POSTS_PER_RUN = 3
MIN_TITLE_LEN = 15
MIN_SUMMARY_LEN = 50
SEND_DELAY = 30


def _pick_articles(new_articles, max_count=MAX_POSTS_PER_RUN):
    """انتخاب مقالات"""
    valid = [
        a for a in new_articles
        if len(a.get("title", "")) >= MIN_TITLE_LEN
        and len(a.get("summary", "")) >= MIN_SUMMARY_LEN
    ]

    random.shuffle(valid)
    return valid[:max_count]


async def run():
    log.info("=" * 55)
    log.info("🏥 ViaChart Medical Bot")
    log.info("=" * 55)

    # ۱. دریافت مقالات
    articles = fetch_all_articles()
    if not articles:
        log.warning("⚠️ هیچ مقاله‌ای دریافت نشد")
        return

    # ۲. فیلتر تکراری‌ها
    seen = load_seen()
    log.info(f"📚 {len(seen)} لینک در حافظه")
    new_articles = filter_new(articles, seen)

    if not new_articles:
        log.info("😐 هیچ مقاله جدیدی وجود ندارد")
        return

    # ۳. انتخاب
    picks = _pick_articles(new_articles, MAX_POSTS_PER_RUN)
    log.info(f"\n🎯 {len(picks)} مقاله انتخاب شد برای ارسال:")
    for p in picks:
        log.info(f"   📰 [{p['source']}] {p['title'][:70]}")

    # ۴. ارسال
    sent = 0
    for i, article in enumerate(picks, 1):
        log.info(f"\n📤 پردازش {i}/{len(picks)}: {article['title'][:60]}...")

        # دریافت متن کامل
        try:
            full_text = fetch_article_full_text(article['link'])
            if full_text:
                article['full_text'] = full_text
                log.info(f"   ✅ متن کامل دریافت شد ({len(full_text)} کاراکتر)")
            else:
                article['full_text'] = article.get('summary', '')
                log.info("   ⚠️ فقط خلاصه در دسترس بود")
        except Exception as e:
            log.warning(f"   ⚠️ خطا در متن کامل: {e}")
            article['full_text'] = article.get('summary', '')

        # ارسال
        try:
            ok = await post_article(article)
            if ok:
                seen = add_to_seen(seen, article)
                sent += 1
                log.info("   ✅ ارسال موفق")
                if i < len(picks):
                    log.info(f"   ⏳ انتظار {SEND_DELAY} ثانیه...")
                    await asyncio.sleep(SEND_DELAY)
        except Exception as e:
            log.error(f"   ❌ خطا: {e}")

    # ۵. ذخیره حافظه
    if sent > 0:
        save_seen(seen)
        log.info(f"\n💾 حافظه ذخیره شد ({len(seen)} لینک)")

    log.info(f"\n🎉 {sent} پست ارسال شد از {len(picks)} کاندیدا")


def main():
    log.info("🎬 شروع اجرا")
    try:
        asyncio.run(run())
        log.info("✅ اجرا تمام شد")
    except Exception as e:
        log.error(f"❌ خطای کلی: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()