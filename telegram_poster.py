import os
import logging
from telegram import Bot, InputFile
from telegram.constants import ParseMode

from pdf_generator import generate_pdf

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
        "مهر سلامت": "#سلامت #اخبار_پزشکی #مهر",
        "ایسنا سلامت": "#سلامت #اخبار_پزشکی #ایسنا",
        "ایرنا سلامت": "#سلامت #اخبار_پزشکی #ایرنا",
        "فارس سلامت": "#سلامت #اخبار_پزشکی",
        "تابناک سلامت": "#سلامت #اخبار_پزشکی",
        "سلامت نیوز": "#سلامت #پزشکی #سلامت_نیوز",
        "بهداشت نیوز": "#سلامت #بهداشت",
        "وزارت بهداشت": "#وزارت_بهداشت #سلامت_عمومی",
    }
    return mapping.get(source, "#پزشکی #سلامت")


def build_caption(article):
    source = article.get("source", "")
    title = article.get("title", "")
    summary = article.get("summary", "")
    link = article.get("link", "").strip()

    summary_short = _truncate(_escape(summary), 600)

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
    parts.append("")
    parts.append("⚠️ صرفاً جهت اطلاع‌رسانی — جایگزین نظر پزشک متخصص نیست.")
    parts.append("")
    parts.append("📄 <b>متن کامل در PDF ضمیمه</b>")

    return "\n".join(parts)


async def send_article(article):
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

    try:
        pdf_path = generate_pdf(article)
        caption = build_caption(article)

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                await bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=InputFile(f, filename=os.path.basename(pdf_path)),
                    caption=caption[:1024],
                    parse_mode=ParseMode.HTML,
                )
            log.info("✅ PDF + کپشن ارسال شد")
            return True
        else:
            log.warning("⚠️ PDF ساخته نشد، فقط متن")
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=caption[:4096],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            return True

    except Exception as e:
        log.error("❌ خطا در ارسال: " + str(e))
        return False


async def post_article(article):
    log.info("📝 ارسال مقاله: " + article.get("title", "")[:60] + "...")
    return await send_article(article)