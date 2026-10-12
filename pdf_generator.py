"""
ساخت فایل PDF از مقاله فارسی
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
    """ثبت فونت فارسی"""
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
            log.warning(f"⚠️ خطا در فونت: {e}")

    if bold_font:
        try:
            pdfmetrics.registerFont(TTFont("PersianFontBold", bold_font))
            log.info(f"✅ فونت بولد: {bold_font}")
        except Exception as e:
            log.warning(f"⚠️ خطا در فونت بولد: {e}")

    return "PersianFont", "PersianFontBold" if bold_font else "PersianFont"


def _fix_persian(text):
    """اصلاح متن فارسی برای PDF"""
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
    ساخت PDF از مقاله فارسی
    """
    try:
        title = article.get("title", "").strip()
        summary = article.get("summary", "").strip()
        full_text = article.get("full_text", "").strip()
        source = article.get("source", "")
        link = article.get("link", "")
        published = article.get("published", "")

        if not title:
            log.warning("⚠️ عنوان خالی، PDF ساخته نشد")
            return None

        # اسم فایل
        filename = f"{_safe_filename(title)}.pdf"
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
            title=title[:80],
        )

        # استایل‌ها
        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            "PersianTitle",
            parent=styles["Title"],
            fontName=bold,
            fontSize=17,
            leading=26,
            alignment=2,
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
            alignment=1,
            textColor=HexColor("#999999"),
            spaceBefore=30,
        )

        # محتوا
        story = []

        # عنوان
        story.append(Paragraph(_fix_persian(title), style_title))

        # متادیتا
        meta_lines = []
        if source:
            meta_lines.append(f"منبع: {source}")
        if published:
            meta_lines.append(f"تاریخ: {published}")
        meta_text = " | ".join(meta_lines)
        if meta_text:
            story.append(Paragraph(_fix_persian(meta_text), style_meta))

        # خلاصه
        if summary:
            story.append(Paragraph(_fix_persian("خلاصه"), style_heading))
            for para in summary.split("\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(_fix_persian(para), style_body))

        # متن کامل
        if full_text and len(full_text) > len(summary) + 100:
            story.append(PageBreak())
            story.append(Paragraph(_fix_persian("متن کامل"), style_heading))

            for para in full_text.split("\n"):
                para = para.strip()
                if para and len(para) > 5:
                    story.append(Paragraph(_fix_persian(para), style_body))

        # فوتر
        story.append(Spacer(1, 20))
        footer_text = (
            f"لینک اصلی:\n{link}\n\n"
            f"کانال تلگرام: @ModernMedFA\n\n"
            "این مطلب صرفاً جنبه اطلاع‌رسانی دارد و جایگزین نظر پزشک متخصص نیست."
        )
        story.append(Paragraph(_fix_persian(footer_text).replace("\n", "<br/>"), style_footer))

        # ساخت
        doc.build(story)
        log.info(f"✅ PDF ساخته شد: {filepath}")
        return filepath

    except Exception as e:
        log.error(f"❌ خطا در ساخت PDF: {e}")
        return None


if __name__ == "__main__":
    test = {
        "title": "تست ساخت PDF فارسی",
        "summary": "این یک خلاصه تست است.\n\nپاراگراف دوم خلاصه.",
        "full_text": "متن کامل مقاله اینجا قرار می‌گیرد.\n\nپاراگراف دوم متن کامل.\n\nپاراگراف سوم.",
        "source": "مهر سلامت",
        "link": "https://example.com",
        "published": "1404/07/20",
    }
    path = generate_pdf(test)
    print(f"PDF: {path}")