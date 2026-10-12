"""
ارسال پست‌های پزشکی به کانال تلگرام
- ترجمه به فارسی
- ساخت PDF کامل
- فقط یک پست (PDF + کپشن)
"""
import os
import logging
from telegram import Bot, InputFile
from telegram.constants import ParseMode

from translator import translate_title, translate_summary, translate_to_fa, _save_cache
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
        "The Lancet": "#ژورنال_کلاب #Lancet #پزشکی_بالینی",
        "BMJ": "#ژورنال_کلاب #BMJ #پزشکی_بالینی",
        "Nature Medicine": "#تحقیقات #NatureMedicine",
        "Nature": "#علمی #Nature",
        "PubMed Cancer": "#انکولوژی #سرطان",
        "PubMed HIV": "#HIV #ایدز",
        "PubMed Infectious": "#عفونی #میکروبیولوژی",
        "bioRxiv": "#پیش_چاپ #bioRxiv",
        "medRxiv": "#پیش_چاپ #medRxiv",
        "WHO": "#سلامت_عمومی #WHO",
        "Mayo Clinic": "#سلامت_عمومی #MayoClinic",
        "MedlinePlus": "#سلامت_عمومی",
        "NIH News": "#سلامت_عمومی #NIH",
    }
    return mapping.get(source, "#پزشکی #سلامت")


def prepare_article(article):
    """ترجمه عنوان، خلاصه و متن کامل"""
    log.info(f"🌐 ترجمه: {article.get('title', '')[:50]}...")

    article["title_fa"] = translate_title(article.get("title", ""))
    article["summary_fa"] = translate_summary(article.get("summary", ""))

    full_text = article.get("full_text", "").strip()
    summary = article.get("summary", "").strip()
    if full_text and len(full_text) > len(summary) + 50:
        log.info("   🌐 ترجمه متن کامل...")
        article["full_text_fa"] = translate_to_fa(full_text[:4000])
    else:
        article["full_text_fa"] = ""

    try:
        _save_cache()
    except Exception:
        pass

    return article


def build_caption(article):
    """ساخت کپشن کوتاه (زیر PDF)"""
    source = article.get("source", "")
    title_fa = article.get("title_fa") or article.get("title", "")
    summary_fa = article.get("summary_fa") or ""
    link = article.get("link", "").strip()

    summary_short = _truncate(_escape(summary_fa), 500)

    parts = [
        f"🔬 <b>{_escape(title_fa)}</b>",
        "",
        f"📖 {summary_short}",
        "",
        f"📚 منبع: <b>{_escape(source)}</b>",
        f"🔗 <a href=\"{link}\">لینک اصلی مقاله</a>",
        "",
        f"🏷 {_hashtags(source)}",
        f"📢 {CHANNEL_HANDLE}",
        "",
        "⚠️ صرفاً جهت اطلاع‌رسانی علمی — جایگزین نظر پزشک متخصص نیست.",
        "",
        "📄 <b>متن کامل ترجمه‌شده در PDF ضمیمه</b>",
    ]

    return "\n".join(parts)


async def send_article(article):
    """ارسال فقط یک پست: PDF + کپشن"""
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
            log.info("✅ PDF + کپشن ارسال شد (یک پست)")
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
        log.error(f"❌ خطا در ارسال: {e}")
        return False


async def post_article(article):
    """تابع اصلی: ترجمه + ارسال"""
    article = prepare_article(article)
    return await send_article(article)