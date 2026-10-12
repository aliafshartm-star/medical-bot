import os
import sys
import asyncio
import logging
import random

from content_fetcher import fetch_all_articles
from seen_tracker import load_seen, save_seen, filter_new, add_to_seen
from telegram_poster import post_article

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════
MAX_POSTS_PER_RUN = 5
SEND_DELAY = 20


def _pick_articles(new_articles, max_count=MAX_POSTS_PER_RUN):
    """انتخاب اخبار برای ارسال"""
    valid = [
        a for a in new_articles
        if len(a.get("title", "")) >= 15
    ]
    random.shuffle(valid)
    return valid[:max_count]


async def run():
    log.info("=" * 55)
    log.info("🏥 ViaChart Medical Bot")
    log.info("=" * 55)

    # ۱. دریافت اخبار
    articles = fetch_all_articles()
    if not articles:
        log.warning("⚠️ هیچ خبری دریافت نشد")
        return

    # ۲. فیلتر تکراری‌ها
    seen = load_seen()
    log.info("📚 " + str(len(seen)) + " لینک در حافظه")
    new_articles = filter_new(articles, seen)

    if not new_articles:
        log.info("😐 هیچ خبر جدیدی وجود ندارد")
        return

    # ۳. انتخاب
    picks = _pick_articles(new_articles, MAX_POSTS_PER_RUN)
    log.info("\n🎯 " + str(len(picks)) + " خبر انتخاب شد:")
    for p in picks:
        img_flag = "🖼" if p.get("image_url") else "📰"
        log.info("   " + img_flag + " [" + p['source'] + "] " + p['title'][:60])

    # ۴. ارسال
    sent = 0
    for i, article in enumerate(picks, 1):
        log.info("\n📤 ارسال " + str(i) + "/" + str(len(picks)) + ": " + article['title'][:60] + "...")

        try:
            ok = await post_article(article)
            if ok:
                seen = add_to_seen(seen, article)
                sent += 1
                log.info("   ✅ ارسال موفق")
                if i < len(picks):
                    await asyncio.sleep(SEND_DELAY)
        except Exception as e:
            log.error("   ❌ خطا: " + str(e))

    # ۵. ذخیره حافظه
    if sent > 0:
        save_seen(seen)
        log.info("\n💾 حافظه ذخیره شد (" + str(len(seen)) + " لینک)")

    log.info("\n🎉 " + str(sent) + " خبر ارسال شد از " + str(len(picks)) + " کاندیدا")


def main():
    log.info("🎬 شروع اجرا")
    try:
        asyncio.run(run())
        log.info("✅ اجرا تمام شد")
    except Exception as e:
        log.error("❌ خطای کلی: " + str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()