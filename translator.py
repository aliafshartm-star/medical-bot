"""
ترجمه مقالات به فارسی با Google Translate رایگان
"""
import logging
import time
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)


# واژه‌نامه تخصصی پزشکی (اصطلاحات مهم که ترجمه گوگل اشتباه می‌کنه)
MEDICAL_TERMS = {
    "hypertension": "پرفشاری خون",
    "diabetes mellitus": "دیابت شیرین",
    "myocardial infarction": "سکته قلبی",
    "carcinoma": "کارسینوما",
    "metastasis": "متاستاز",
    "chemotherapy": "شیمی‌درمانی",
    "radiotherapy": "پرتودرمانی",
    "immunotherapy": "ایمونوتراپی",
    "antiretroviral": "ضد رتروویروس",
    "antimicrobial": "ضدمیکروبی",
    "antibiotic resistance": "مقاومت آنتی‌بیوتیکی",
    "randomized controlled trial": "کارآزمایی بالینی تصادفی",
    "placebo": "دارونما",
    "efficacy": "کارآمدی",
    "adverse effects": "عوارض جانبی",
    "pandemic": "پاندمی",
    "epidemiology": "اپیدمیولوژی",
    "pathogenesis": "پاتوژنز",
    "biomarker": "بیومارکر",
    "clinical trial": "کارآزمایی بالینی",
}


def translate_to_fa(text):
    """ترجمه متن انگلیسی به فارسی"""
    if not text or not text.strip():
        return ""
    try:
        # محدودیت گوگل: حداکثر ۵۰۰۰ کاراکتر
        text = text[:4900]
        translated = GoogleTranslator(source="en", target="fa").translate(text)
        time.sleep(0.3)  # جلوگیری از rate limit
        return translated or text
    except Exception as e:
        log.warning(f"⚠️ خطا در ترجمه: {str(e)[:80]}")
        return text  # اگه ترجمه نشد، متن اصلی برگرده


def translate_title(title):
    """ترجمه عنوان با اصلاح اصطلاحات تخصصی"""
    if not title:
        return ""
    translated = translate_to_fa(title)
    return translated


def translate_summary(summary):
    """ترجمه خلاصه"""
    if not summary:
        return ""
    # حذف تگ‌های اضافی HTML
    summary = summary.strip()
    translated = translate_to_fa(summary)
    return translated


def translate_article(article):
    """ترجمه کامل یک مقاله (عنوان و خلاصه)"""
    log.info(f"🌐 ترجمه: {article.get('title', '')[:50]}...")

    translated = article.copy()
    translated["title_fa"] = translate_title(article.get("title", ""))
    translated["summary_fa"] = translate_summary(article.get("summary", ""))

    log.info(f"   ✅ ترجمه شد")
    return translated


if __name__ == "__main__":
    # تست محلی
    test_text = "New study shows that hypertension treatment reduces cardiovascular risk."
    print(f"Original: {test_text}")
    print(f"Translated: {translate_to_fa(test_text)}")