import os
import logging
import requests
from telegram import Bot, InputFile
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@ModernMedFA")
CHANNEL_HANDLE = "@ModernMedFA"


def _escape(text):
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
    mapping = {
        "سلامت نیوز": "#سلامت #پزشکی #سلامت_نیوز",
        "بهداشت نیوز": "#سلامت #بهداشت",
        "طبنا": "#سلامت #پزشکی",
        "شفاآنلاین": "#سلامت #پزشکی",
        "سیناپرس سلامت": "#سلامت #علمی #سیناپرس",
        "مهر سلامت": "#سلامت #اخبار_پزشکی",
        "ایسنا سلامت": "#سلامت #اخبار_پزشکی",
    }
    return mapping.get(source, "#پزشکی #سلامت")


def _download_image(url):
    """دانلود عکس خبر"""
    if not url:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MedicalBot/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        ext = ".jpg"
        content_type = response.headers.get("Content-Type", "").lower()
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"

        path = "temp_image" + ext
        with open(path, "wb") as f:
            f.write(response.content)

        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 5:
            os.remove(path)
            log.warning("   ⚠️ عکس بزرگ‌تر از ۵MB")
            return None

        return path
    except Exception as e:
        log.warning("   ⚠️ خطا در دانلود عکس: " + str(e)[:60])
        return None


def build_caption(article):
    """ساخت کپشن خبر"""
    source = article.get("source", "")
    title = article.get("title", "")
    summary = article.get("summary", "")
    link = article.get("link", "").strip()

    summary_short = _truncate(_escape(summary), 700)

    parts = [
        "🩺 <b>" + _escape(title) + "</b>",
        "",
    ]

    if summary_short:
        parts.append("📖 " + summary_short)
        parts.append("")

    parts.append("📚 منبع: <b>" + _escape(source) + "</b>")
    parts.append('🔗 <a href="' + link + '">لینک خبر</a>')
    parts.append("")
    parts.append("🏷 " + _hashtags(source))
    parts.append("📢 " + CHANNEL_HANDLE)

    return "\n".join(parts)


async def send_article(article):
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

    try:
        caption = build_caption(article)
        image_url = article.get("image_url")

        # تلاش برای ارسال با عکس
        if image_url:
            log.info("   🖼 دانلود عکس...")
            img_path = _download_image(image_url)

            if img_path and os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        await bot.send_photo(
                            chat_id=CHANNEL_ID,
                            photo=InputFile(f),
                            caption=caption[:1024],
                            parse_mode=ParseMode.HTML,
                        )
                    log.info("   ✅ عکس + کپشن ارسال شد")
                    os.remove(img_path)
                    return True
                except Exception as e:
                    log.warning("   ⚠️ خطا در ارسال عکس: " + str(e)[:60])
                    if os.path.exists(img_path):
                        os.remove(img_path)

        # اگه عکس نداشت یا خطا داد → فقط متن
        log.info("   📰 فقط متن (بدون عکس)")
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=caption[:4096],
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )
        log.info("   ✅ پیام متنی ارسال شد")
        return True

    except Exception as e:
        log.error("❌ خطا در ارسال: " + str(e))
        return False


async def post_article(article):
    log.info("📝 ارسال خبر: " + article.get("title", "")[:60] + "...")
    return await send_article(article)