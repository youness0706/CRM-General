# payments/invoice_views.py
"""
Lightweight Invoice Generation using ReportLab only
Arabic RTL supported (reshaping + bidi)
No WeasyPrint, no HTML templates, pure Python
"""

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.contrib.staticfiles import finders

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from io import BytesIO
import hashlib
import os

import arabic_reshaper
from bidi.algorithm import get_display

from ..models import Payments


# ======================================================
# Fonts (Unicode Arabic)
# ======================================================

FONT_DIR = os.path.join(settings.BASE_DIR, "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")

if not os.path.exists(FONT_REGULAR):
    raise RuntimeError(f"Font not found: {FONT_REGULAR}")
if not os.path.exists(FONT_BOLD):
    raise RuntimeError(f"Font not found: {FONT_BOLD}")

pdfmetrics.registerFont(TTFont("DejaVu", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))


# ======================================================
# Arabic helper
# ======================================================

def ar(text: str) -> str:
    """Reshape + apply bidi to Arabic text"""
    if text is None:
        return ""
    text = str(text).strip()
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


# ======================================================
# Invoice number
# ======================================================

def generate_invoice_number(payment_id, payment_date):
    """
    Deterministic invoice number
    Format: INV-YYYY-XXXXXX
    """
    base = f"{payment_id}-{payment_date.isoformat()}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:6].upper()
    return f"INV-{payment_date.year}-{digest}"


# ======================================================
# Static logo helper
# ======================================================

def get_saas_logo_path() -> str | None:
    """
    Returns an absolute file path for static/logo/logo.png
    Works with dev and collectstatic (STATICFILES_STORAGE).
    """
    p = settings.BASE_DIR / "staticfiles/images/logo/logo.png"
    return p if p and os.path.exists(p) else None


# ======================================================
# Main view
# ======================================================

@login_required
def download_payment_invoice(request, payment_id):
    payment = get_object_or_404(
        Payments.objects.select_related("trainer", "organization"),
        id=payment_id
    )

    # Security check (kept as you had)
    if not getattr(request, "organization", None) or request.organization.id != payment.organization.id:
        raise Http404("Payment not found")

    org = payment.organization
    trainer = payment.trainer

    invoice_number = generate_invoice_number(payment.id, payment.paymentdate)

    PAYMENT_CATEGORIES = {
        "month": ar("اشتراك شهري"),
        "subscription": ar("رسوم الانخراط"),
        "assurance": ar("التأمين"),
        "jawaz": ar("جواز"),
    }
    category = PAYMENT_CATEGORIES.get(payment.paymentCategry, ar(payment.paymentCategry))

    # Money
    amount = float(payment.paymentAmount or 0)
    tax_rate = 0.0  # Morocco SaaS default (receipt); keep shown as 0%
    tax_amount = round(amount * tax_rate, 2)
    total = round(amount + tax_amount, 2)

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=str(invoice_number),
    )

    elements = []
    styles = getSampleStyleSheet()

    # Base styles
    style_normal_ar = ParagraphStyle(
        "NormalAR",
        parent=styles["Normal"],
        fontName="DejaVu",
        fontSize=10,
        leading=16,
        alignment=TA_RIGHT,
    )

    style_small_center = ParagraphStyle(
        "SmallCenter",
        parent=styles["Normal"],
        fontName="DejaVu",
        fontSize=8,
        leading=12,
        alignment=TA_CENTER,
        textColor=HexColor("#6b7280"),
    )

    # Colors
    C_PRIMARY = HexColor("#2c3e50")
    C_ACCENT = HexColor("#3c78e7")
    C_GRID = HexColor("#d7dce3")
    C_NOTE_BG = HexColor("#fff7cc")
    C_NOTE_BORDER = HexColor("#f39c12")

    # Layout widths
    PAGE_W = 16.2 * cm  # approx after margins
    LABEL_W = 5.2 * cm
    VALUE_W = PAGE_W - LABEL_W

    def section_header(title: str):
        t = Table([[ar(title)]], colWidths=[PAGE_W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "DejaVu-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return t

    def kv_table(rows):
        """
        rows: list[tuple[label, value]] (both already strings)
        """
        data = [[ar(lbl), ar(val)] for (lbl, val) in rows]
        t = Table(data, colWidths=[LABEL_W, VALUE_W])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "DejaVu-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "DejaVu"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.6, C_GRID),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    # ==================================================
    # Top row: SaaS logo + Title bar
    # ==================================================

    logo_path = get_saas_logo_path()
    logo_cell = ""
    if logo_path:
        try:
            logo_cell = Image(logo_path, width=3.2 * cm, height=1.6 * cm)
        except Exception:
            logo_cell = ""

    title_table = Table(
        [[logo_cell, ar("إيصال دفع")]],
        colWidths=[4.0 * cm, PAGE_W - 4.0 * cm]
    )
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (1, 0), (1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (1, 0), (1, 0), 18),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 0.5 * cm))

    # ==================================================
    # Invoice meta
    # ==================================================

    meta = kv_table([
        (timezone.now().strftime("%Y/%m/%d"),"التاريخ"),
        (invoice_number,"رقم الفاتورة"),
        (payment.paymentdate.strftime("%Y/%m/%d"),"تاريخ الدفع"),
    ])
    meta_wrap = Table([[meta]], colWidths=[PAGE_W])
    meta_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, C_PRIMARY),
        ("INNERPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(meta_wrap)
    elements.append(Spacer(1, 0.55 * cm))

    # ==================================================
    # Organization
    # ==================================================
    elements.append(section_header("معلومات الجمعية"))
    elements.append(Spacer(1, 0.25 * cm))

    org_rows = [(getattr(org, "name", ""), "الاسم")]
    if getattr(org, "location", None):
        org_rows.append((org.location, "العنوان"))
    if getattr(org, "phone_number", None):
        org_rows.append((org.phone_number, "الهاتف"))
    if getattr(org, "email", None):
        org_rows.append((org.email, "البريد الإلكتروني"))

    elements.append(kv_table(org_rows))
    elements.append(Spacer(1, 0.55 * cm))

    # ==================================================
    # Client
    # ==================================================
    elements.append(section_header("معلومات العميل"))
    elements.append(Spacer(1, 0.25 * cm))

    full_name = getattr(trainer, "full_name", "") or f"{getattr(trainer, 'first_name', '')} {getattr(trainer, 'last_name', '')}".strip()
    client_rows = [(full_name, "الاسم")]

    if getattr(trainer, "CIN", None):
        client_rows.append((trainer.CIN, "البطاقة الوطنية"))

    phone = getattr(trainer, "phone", None) or getattr(trainer, "phone_parent", None)
    if phone:
        client_rows.append((phone, "الهاتف"))
    if getattr(trainer, "email", None):
        client_rows.append((trainer.email, "البريد الإلكتروني"))

    elements.append(kv_table(client_rows))
    elements.append(Spacer(1, 0.55 * cm))

    # ==================================================
    # Payment details table
    # ==================================================
    elements.append(section_header("تفاصيل الدفع"))
    elements.append(Spacer(1, 0.25 * cm))

    pay_data = [
        [ar("الوصف"), ar("التاريخ"), ar("المبلغ")],
        [category, ar(payment.paymentdate.strftime("%Y/%m/%d")), f"{amount:.2f} MAD"],
    ]
    pay_table = Table(pay_data, colWidths=[9.0 * cm, 4.0 * cm, PAGE_W - 13.0 * cm])
    pay_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),

        ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (0, 1), (0, 1), "RIGHT"),
        ("ALIGN", (1, 1), (1, 1), "CENTER"),
        ("ALIGN", (2, 1), (2, 1), "CENTER"),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),

        ("BOX", (0, 0), (-1, -1), 1, C_PRIMARY),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, C_GRID),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 0.45 * cm))

    # ==================================================
    # Totals (clean right block)
    # ==================================================
    totals_data = [
        [ar("المجموع الفرعي"), f"{amount:.2f} MAD"],
        [ar(f"الضريبة ({int(tax_rate * 100)}%)"), f"{tax_amount:.2f} MAD"],
        [ar("المجموع الإجمالي"), f"{total:.2f} MAD"],
    ]
    totals_table = Table(totals_data, colWidths=[LABEL_W, VALUE_W])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -2), "DejaVu"),
        ("FONTNAME", (1, 0), (1, -2), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -2), 10),

        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.6, C_GRID),

        # Total row highlight
        ("BACKGROUND", (0, 2), (1, 2), C_PRIMARY),
        ("TEXTCOLOR", (0, 2), (1, 2), colors.white),
        ("FONTNAME", (0, 2), (1, 2), "DejaVu-Bold"),
        ("FONTSIZE", (0, 2), (1, 2), 11),

        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, C_PRIMARY),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.55 * cm))

    # ==================================================
    # Notes
    # ==================================================
    notes_text = ar(
        "ملاحظات\n"
        "• هذه الوثيقة عبارة عن إيصال دفع تم إنشاؤه إلكترونياً\n"
        "• يُرجى الاحتفاظ بهذا الإيصال كإثبات للدفع\n"
        "• لأي استفسارات، يُرجى التواصل مع الجمعية"
    )
    notes_table = Table([[notes_text]], colWidths=[PAGE_W])
    notes_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_NOTE_BG),
        ("BOX", (0, 0), (-1, -1), 1, C_NOTE_BORDER),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(notes_table)
    elements.append(Spacer(1, 0.6 * cm))

    # ==================================================
    # Footer
    # ==================================================
    footer_text = ar(
        f"تم إنشاء هذه الفاتورة بتاريخ {timezone.now().strftime('%Y/%m/%d %H:%M')}  |  "
        f"{getattr(org, 'name', '')} - جميع الحقوق محفوظة © {timezone.now().year}"
    )
    elements.append(Paragraph(footer_text, style_small_center))

    # Build PDF
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{invoice_number}.pdf"'
    return response
