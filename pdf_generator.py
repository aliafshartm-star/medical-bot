"""
ساخت فایل PDF از مقاله ترجمه‌شده
"""
import os
import logging
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


def _register_persian_font():
    """ثبت فونت فارسی برای PDF"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ]

    regular_font = None
    bold_font = None

    for path in font_paths:
        if os.path.exists(path):
            if "Bold" in path and bold_font is None:
                bold_font = path
            elif "Bold" not in path and regular_font is None:
                regular_font = path

    if regular_font:
        try:
            pdfmetrics.registerFont(TTFont("PersianFont", regular_font))
            log.info(f"✅ فونت عادی: {regular_font}")
        except Exception as e:
            log.warning(f"⚠️ خطا در فونت عادی: {e}")

    if bold_font:
        try:
            pdfmetrics.registerFont(TTFont("PersianFontBold", bold_font))
            log.info(f"✅ فونت بولد: {bold_font}")
        except Exception as e:
            log.warning(f"⚠️ خطا در فونت بولد: {e}")

    return "PersianFont", "PersianFontBold" if bold_font else "PersianFont"


def _fix_persian(text):
    """اصلاح متن فارسی برای PDF (راست‌چین + اتصال حروف)"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def _safe_filename(text, max_len=40):
    """ساخت اسم فایل امن"""
    safe = "".join(c for c in text if c.isalnum() or c in " -_")
    safe = safe.strip().replace(" ", "_")
    return safe[:max_len] if safe else "article"


def generate_pdf(article):
    """
    ساخت PDF از مقاله
    برمی‌گردونه: مسیر فایل PDF یا None
    """
    try:
        title_fa = article.get("title_fa") or article.get("title", "")
        summary_fa = article.get("summary_fa") or article.get("summary", "")
        full_text_fa = article.get("full_text_fa", "") or article.get("full_text", "")
        source = article.get("source", "")
        link = article.get("link", "")
        published = article.get("published", "")

        # اسم فایل
        filename = f"{_safe_filename(title_fa)}.pdf"
        filepath = os.path.join(PDF_DIR, filename)

        # ثبت فونت
        regular, bold = _register_persian_font()

        # ساخت PDF
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=title_fa[:80],
        )

        # استایل‌ها
        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            "PersianTitle",
            parent=styles["Title"],
            fontName=bold,
            fontSize=18,
            leading=26,
            alignment=2,  # راست‌چین
            textColor=HexColor("#1a5490"),
            spaceAfter=15,
        )

        style_meta = ParagraphStyle(
            "PersianMeta",
            parent=styles["Normal"],
            fontName=regular,
            fontSize=10,
            leading=16,
            alignment=2,
            textColor=HexColor("#666666"),
            spaceAfter=20,
        )

        style_body = ParagraphStyle(
            "PersianBody",
            parent=styles["Normal"],
            fontName=regular,
            fontSize=11,
            leading=20,
            alignment=2,
            spaceAfter=10,
        )

        style_heading = ParagraphStyle(
            "PersianHeading",
            parent=styles["Heading2"],
            fontName=bold,
            fontSize=14,
            leading=22,
            alignment=2,
            textColor=HexColor("#1a5490"),
            spaceBefore=15,
            spaceAfter=10,
        )

        style_footer = ParagraphStyle(
            "PersianFooter",
            parent=styles["Normal"],
            fontName=regular,
            fontSize=9,
            leading=14,
            alignment=1,  # وسط
            textColor=HexColor("#999999"),
            spaceBefore=30,
        )

        # محتوا
        story = []

        # عنوان
        story.append(Paragraph(_fix_persian(title_fa), style_title))

        # متادیتا
        meta_lines = []
        if source:
            meta_lines.append(f"📚 منبع: {source}")
        if published:
            meta_lines.append(f"🗓 تاریخ: {published}")
        meta_text = " | ".join(meta_lines)
        if meta_text:
            story.append(Paragraph(_fix_persian(meta_text), style_meta))

        # بخش خلاصه
        story.append(Paragraph(_fix_persian("📖 خلاصه"), style_heading))

        summary_text = summary_fa or "خلاصه‌ای در دسترس نیست."
        # تقسیم به پاراگراف
        for para in summary_text.split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(_fix_persian(para), style_body))

        # بخش متن کامل (اگه داشتیم)
        if full_text_fa and len(full_text_fa) > len(summary_fa) + 100:
            story.append(PageBreak())
            story.append(Paragraph(_fix_persian("📄 متن کامل مقاله"), style_heading))

            for para in full_text_fa.split("\n"):
                para = para.strip()
                if para and len(para) > 5:
                    story.append(Paragraph(_fix_persian(para), style_body))

        # فوتر
        story.append(Spacer(1, 20))
        footer_text = (
            f"🔗 لینک اصلی مقاله:\n{link}\n\n"
            f"📢 کانال تلگرام: @ModernMedFA\n\n"
            "⚠️ این مطلب صرفاً جنبه اطلاع‌رسانی علمی دارد و جایگزین نظر پزشک متخصص نیست."
        )
        story.append(Paragraph(_fix_persian(footer_text).replace("\n", "<br/>"), style_footer))

        # ساخت PDF
        doc.build(story)
        log.info(f"✅ PDF ساخته شد: {filepath}")
        return filepath

    except Exception as e:
        log.error(f"❌ خطا در ساخت PDF: {e}")
        return None


if __name__ == "__main__":
    test_article = {
        "title": "Test Article",
        "title_fa": "مقاله تست",
        "summary": "Test summary",
        "summary_fa": "این یک خلاصه تست است برای بررسی عملکرد ساخت PDF فارسی.",
        "full_text_fa": "این متن کامل مقاله تست است.\n\nاین پاراگراف دوم است.\n\nو این هم پاراگراف سوم.",
        "source": "NEJM",
        "link": "https://example.com",
        "published": "2026-10-12",
    }
    path = generate_pdf(test_article)
    print(f"PDF: {path}")