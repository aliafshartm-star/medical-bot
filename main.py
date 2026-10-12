"""
ViaChart Medical Bot - اجرای اصلی
- دریافت مقالات از منابع معتبر
- فیلتر مقالات تکراری
- ارسال به کانال تلگرام
"""
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
MAX_POSTS_PER_RUN = 3          # حداکثر چند پست در هر اجرا
SPECIALIZED_RATIO = 0.6        # ۶۰٪ تخصصی، ۴۰٪ عمومی
MIN_SUMMARY_LEN = 50           # حداقل طول خلاصه مقاله
SEND_DELAY = 30                # ثانیه فاصله بین پست‌ها


def _pick_articles(new_articles, max_count=MAX_POSTS_PER_RUN):
    """
    انتخاب مقالات با نسبت تخصصی/عمومی
    """
    specialized = [a for a in new_articles if a.get("category") == "specialized"]
    general = [a for a in new_articles if a.get("category") == "general"]

    # فیلتر بر اساس طول خلاصه
    specialized = [a for a in specialized if len(a.get("summary", "")) >= MIN_SUMMARY_LEN]
    general = [a for a in general if len(a.get("summary", "")) >= MIN_SUMMARY_LEN]

    # شافل کردن برای تنوع
    random.shuffle(specialized)
    random.shuffle(general)

    # تعداد از هر دسته
    n_spec = min(len(specialized), max(1, int(max_count * SPECIALIZED_RATIO)))
    n_gen = min(len(general), max_count - n_spec)

    picked = []
    picked.extend(specialized[:n_spec])
    picked.extend(general[:n_gen])

    # اگه تعداد کمتر از حد مطلوب شد، از بقیه پر کن
    remaining = max_count - len(picked)
    if remaining > 0:
        rest = specialized[n_spec:] + general[n_gen:]
        random.shuffle(rest)
        picked.extend(rest[:remaining])

    return picked[:max_count]


async def run():
    log.info("=" * 55)
    log.info("🏥 ViaChart Medical Bot")
    log.info("=" * 55)

    # ۱. دریافت مقالات
    articles = fetch_all_articles()
    if not articles:
        log.warning("⚠️ هیچ مقاله‌ای دریافت نشد")
        return

    # ۲. فیلتر مقالات تکراری
    seen = load_seen()
    log.info(f"📚 {len(seen)} لینک در حافظه")
    new_articles = filter_new(articles, seen)

    if not new_articles:
        log.info("😐 هیچ مقاله جدیدی وجود ندارد")
        return

    # ۳. انتخاب مقالات برای ارسال
    picks = _pick_articles(new_articles, MAX_POSTS_PER_RUN)
    log.info(f"\n🎯 {len(picks)} مقاله انتخاب شد برای ارسال:")
    for p in picks:
        cat = "🔬" if p.get("category") == "specialized" else "🩺"
        log.info(f"   {cat} [{p['source']}] {p['title'][:70]}")

    # ۴. ارسال یکی یکی
    sent = 0
    for i, article in enumerate(picks, 1):
        log.info(f"\n📤 ارسال {i}/{len(picks)}...")
        try:
            ok = await post_article(article)
            if ok:
                seen = add_to_seen(seen, article)
                sent += 1
                log.info(f"   ✅ ارسال موفق")
                if i < len(picks):
                    log.info(f"   ⏳ انتظار {SEND_DELAY} ثانیه...")
                    await asyncio.sleep(SEND_DELAY)
            else:
                log.warning(f"   ⚠️ ارسال ناموفق")
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