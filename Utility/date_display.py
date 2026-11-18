"""प्रिंटवर तारीख DD-MM-YYYY स्वरूपात दाखवण्यासाठी (फक्त दाखवणे - साठवलेली किंमत बदलत नाही).

DB / API मधून तारीख "YYYY-MM-DD" (कधी पुढे वेळ: "2026-11-18 00:00:00" / "2026-11-18T10:20")
किंवा date/datetime म्हणून येते. ती "18-11-2026" होते. इतर काहीही (रिकामे, आधीच DD-MM-YYYY,
ओळखू न येणारा मजकूर) जसेच्या तसे परत - त्यामुळे जुन्या/वेगळ्या स्वरूपाची किंमत असली तरी प्रिंट तुटत नाही.
Jinja मध्ये filter म्हणून: {{ value|dmy }}
"""
import re
from datetime import date, datetime

_ISO = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?\s*$")


def to_dmy(value):
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%m-%Y")
    s = str(value)
    m = _ISO.match(s)
    if not m:
        return s
    y, mo, d = m.groups()
    return f"{int(d):02d}-{int(mo):02d}-{y}"
