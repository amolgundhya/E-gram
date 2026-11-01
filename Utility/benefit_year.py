import re
from datetime import datetime

_DATE_FORMATS = ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d', '%Y/%m/%d')


# शौचालय/घरकुल लाभ वर्ष रिपोर्टमध्ये पूर्ण आर्थिक वर्ष "2020-2021" याच स्वरूपात दाखवण्यासाठी -
# युजरने तारीख टाकली असली तरी रिपोर्टमध्ये तारीख नाही, फक्त वर्ष (क्लायंटची मागणी).
# "2020" -> "2020-2021", "2020-21"/"2020-2021" -> "2020-2021", पूर्ण तारीख ("12/06/2020",
# "2020-06-12") असल्यास एप्रिल-मार्च आर्थिक वर्ष (15/02/2021 -> "2020-2021"). काहीच ओळखता
# न आल्यास टाईप केलेलं जसंच्या तसं परत करतो.
def financial_year_full(value):
    if value is None:
        return ''
    s = str(value).strip()
    if not s:
        return ''
    y = None
    m = re.fullmatch(r'(\d{4})', s) or re.fullmatch(r'(\d{4})\s*-\s*(?:\d{2}|\d{4})', s)
    if m:
        y = int(m.group(1))
    else:
        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(s[:10], fmt)
            except ValueError:
                continue
            y = parsed.year if parsed.month >= 4 else parsed.year - 1
            break
    if y is None:
        return s
    return "{}-{}".format(y, y + 1)
