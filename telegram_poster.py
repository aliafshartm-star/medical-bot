"""
ارسال پست‌های پزشکی به کانال تلگرام
"""
import os
import logging
import asyncio
from telegram import Bot
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# کانال مقصد
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@ModernMedFA")
CHANNEL_HANDLE = "@ModernMedFA"


def _escape(text):
    """جلوگیری از خراب شدن HTML"""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _truncate(text, max_len):
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."


def _hashtags(source):
    """ساخت هشتگ بر اساس منبع"""
    mapping = {
        "NEJM": "#ژورنال_کلاب #NEJM #پزشکی_بالینی",
        "The Lancet": "#ژورنال_کلاب #Lancet #پزشکی_بالینی",
        "JAMA": "#ژورنال_کلاب #JAMA #پزشکی_بالینی",
        "BMJ": "#ژورنال_کلاب #BMJ #پزشکی_بالینی",
        "Nature Medicine": "#ژورنال_کلاب #NatureMedicine #تحقیقات",
        "CDC EID": "#عفونی #CDC #اپیدمیولوژی",
        "PubMed Oncology": "#انکولوژی #سرطان #ژورنال_کلاب",
        "PubMed HIV": "#HIV #ایدز #عفونی",
        "PubMed Infectious": "#عفونی #میکروبیولوژی",
        "WHO": "#سلامت_عمومی #WHO",
        "Mayo Clinic": "#سلامت_عمومی #MayoClinic",
        "MedlinePlus": "#سلامت_عمومی",
        "NIH News": "#سلامت_عمومی #NIH #تحقیقات",
    }
    return mapping.get(source, "#پزشکی #سلامت")


def build_post(article):
    """ساخت متن پست بر اساس مقاله"""
    source = article.get("source", "")
    category = article.get("category", "general")
    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()
    link = article.get("link", "").strip()
    published = article.get("published", "").strip()

    # ایموجی و برچسب بر اساس دسته
    if category == "specialized":
        icon = "🔬"
        label = "مقاله تخصصی"
    else:
        icon = "🩺"
        label = "سلامت عمومی"

    # خلاصه (کوتاه)
    summary_short = _truncate(_escape(summary), 700)

    parts = [
        f"{icon} <b>{_escape(title)}</b>",
        "",
    ]

    if summary_short:
        parts.append(f"📖 {summary_short}")
        parts.append("")

    if published:
        parts.append(f"🗓 {_escape(published)}")

    parts.append(f"📚 منبع: <b>{_escape(source)}</b>")
    parts.append(f"🔗 <a href=\"{link}\">متن کامل مقاله</a>")
    parts.append("")
    parts.append(f"🏷 {_hashtags(source)}")
    parts.append(f"📢 {CHANNEL_HANDLE}")
    parts.append("")
    parts.append("⚠️ این مطلب صرفاً جنبه اطلاع‌رسانی علمی دارد و جایگزین نظر پزشک متخصص نیست.")

    return "\n".join(parts)


async def send_post(text):
    """ارسال پست به کانال"""
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text[:4096],
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )
        log.info("✅ پست ارسال شد")
        return True
    except Exception as e:
        log.error(f"❌ خطا در ارسال: {e}")
        return False


async def post_article(article):
    """ساخت و ارسال یک مقاله"""
    log.info(f"📝 ساخت پست: {article.get('title', '')[:60]}...")
    post_text = build_post(article)
    log.info(f"\n{post_text}\n")
    return await send_post(post_text)


if __name__ == "__main__":
    # تست محلی
    test_article = {
        "source": "WHO",
        "category": "general",
        "title": "New guidelines for hypertension management",
        "summary": "WHO released updated guidelines for the management of hypertension in adults, emphasizing lifestyle changes and early intervention.",
        "link": "https://www.who.int/",
        "published": "Mon, 12 Oct 2026 10:00:00 GMT",
    }

    async def _test():
        ok = await post_article(test_article)
        if ok:
            log.info("🎉 تست موفق")
        else:
            log.error("❌ تست ناموفق")
            raise SystemExit(1)

    asyncio.run(_test())