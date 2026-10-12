"""
ارسال پست‌های پزشکی به کانال تلگرام
- ترجمه به فارسی
- ساخت PDF
- ارسال متن + PDF
"""
import os
import logging
import asyncio
from telegram import Bot, InputFile
from telegram.constants import ParseMode

from translator import translate_title, translate_summary, translate_to_fa
from pdf_generator import generate_pdf

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
        "PMC Open Access": "#مقاله_رایگان #OpenAccess",
        "Europe PMC": "#مقاله_رایگان #EuropePMC",
        "DOAJ": "#مقاله_رایگان #DOAJ",
        "medRxiv": "#پیش_چاپ #medRxiv",
        "WHO": "#سلامت_عمومی #WHO",
        "Mayo Clinic": "#سلامت_عمومی #MayoClinic",
        "MedlinePlus": "#سلامت_عمومی",
        "NIH News": "#سلامت_عمومی #NIH #تحقیقات",
    }
    return mapping.get(source, "#پزشکی #سلامت")


def prepare_article(article):
    """
    آماده‌سازی مقاله:
    - ترجمه عنوان و خلاصه
    - ترجمه متن کامل (اگه داشتیم)
    """
    log.info(f"🌐 پردازش: {article.get('title', '')[:50]}...")

    # ترجمه
    article["title_fa"] = translate_title(article.get("title", ""))
    article["summary_fa"] = translate_summary(article.get("summary", ""))

    # ترجمه متن کامل (اگه داشتیم)
    full_text = article.get("full_text", "").strip()
    summary = article.get("summary", "").strip()
    if full_text and len(full_text) > len(summary) + 100:
        log.info("   🌐 ترجمه متن کامل...")
        article["full_text_fa"] = translate_to_fa(full_text)
    else:
        article["full_text_fa"] = ""

    return article


def build_caption(article):
    """ساخت متن کپشن (زیر PDF)"""
    source = article.get("source", "")
    title_fa = article.get("title_fa") or article.get("title", "")
    summary_fa = article.get("summary_fa") or article.get("summary", "")
    link = article.get("link", "").strip()
    category = article.get("category", "specialized")

    if category == "specialized":
        icon = "🔬"
        label = "مقاله تخصصی"
    else:
        icon = "🩺"
        label = "سلامت عمومی"

    # کپشن (حداکثر ۱۰۲۴ کاراکتر برای عکس/فایل)
    summary_short = _truncate(_escape(summary_fa), 500)

    parts = [
        f"{icon} <b>{_escape(title_fa)}</b>",
        "",
        f"📖 {summary_short}",
        "",
        f"📚 منبع: <b>{_escape(source)}</b>",
        f"🔗 <a href=\"{link}\">لینک اصلی مقاله</a>",
        "",
        f"🏷 {_hashtags(source)}",
        f"📢 {CHANNEL_HANDLE}",
        "",
        "⚠️ این مطلب صرفاً جنبه اطلاع‌رسانی علمی دارد و جایگزین نظر پزشک متخصص نیست.",
        "",
        "📄 <b>فایل PDF ترجمه‌شده در پیام بعدی ارسال می‌شود.</b>",
    ]

    return "\n".join(parts)


async def send_article(article):
    """
    ارسال مقاله:
    - پیام متنی اول
    - سپس PDF
    """
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])

    try:
        # ۱. ساخت PDF
        pdf_path = generate_pdf(article)

        # ۲. ساخت کپشن
        caption = build_caption(article)

        # ۳. ارسال PDF با کپشن
        if pdf_path and os.path.exists(pdf_path):
            # PDF حجمش کمه، پس با کپشن بفرست
            with open(pdf_path, "rb") as f:
                await bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=InputFile(f, filename=os.path.basename(pdf_path)),
                    caption=caption[:1024],
                    parse_mode=ParseMode.HTML,
                )
            log.info("✅ PDF + کپشن ارسال شد")

            # اگه متن کامل ترجمه شده بود ولی توی PDF نیومده، ادامه رو بفرست
            full_text_fa = article.get("full_text_fa", "")
            if full_text_fa and len(full_text_fa) > 2000:
                remaining = full_text_fa[2000:]
                if len(remaining) > 100:
                    for chunk_start in range(0, len(remaining), 4000):
                        chunk = remaining[chunk_start:chunk_start + 4000]
                        if chunk.strip():
                            await bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=chunk,
                                parse_mode=ParseMode.HTML,
                            )
                            await asyncio.sleep(2)
            return True
        else:
            # اگه PDF نشد، فقط متن بفرست
            log.warning("⚠️ PDF ساخته نشد، فقط متن ارسال می‌شود")
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
    """تابع اصلی: آماده‌سازی + ارسال"""
    log.info(f"📝 پردازش مقاله: {article.get('title', '')[:60]}...")

    # ۱. ترجمه
    article = prepare_article(article)

    # ۲. ارسال
    return await send_article(article)


if __name__ == "__main__":
    # تست محلی
    test_article = {
        "source": "NEJM",
        "category": "specialized",
        "title": "Vasopressors or Fluids in Early Septic Shock",
        "summary": "The optimal approach to early resuscitation in septic shock is unknown.",
        "full_text": "Sepsis is a life-threatening condition. Early resuscitation is critical.",
        "link": "https://www.nejm.org/",
        "published": "Mon, 12 Oct 2026",
    }

    async def _test():
        ok = await post_article(test_article)
        if ok:
            log.info("🎉 تست موفق")
        else:
            log.error("❌ تست ناموفق")
            raise SystemExit(1)

    asyncio.run(_test())