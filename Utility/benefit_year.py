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


# शौचालय / घरकुल प्रिंटवरील मजकूर - सर्व नमुना-8 प्रिंट्स (single, range, P1/P2, register
# प्रकार 1-5, विशेष पाणी) व Index यादी याच दोन helpers ने छापतात (क्लायंट 24-Nov-2026).
# फक्त दाखवणे - डेटा बदलत नाही. लेबल ("शौचालय :") template मध्येच राहते, इथे फक्त मजकूर.
#   शौचालय: आहे+वर्ष -> "सन <वर्ष> शौचालयाचा लाभ मिळालेला आहे." | आहे, वर्ष नाही -> "आहे"
#           नाही -> "नाही" | निवडले नाही -> ""
#   घरकुल:  योजना+वर्ष -> "<योजना> सन <वर्ष> योजनेचा लाभ मिळाला आहे." | योजना, वर्ष नाही ->
#           "आहे – <योजना>" | नाही -> "नाही" | निवडले नाही -> "" (आहे पण योजना नाही -> "आहे")
def _clean(value):
    return '' if value is None else str(value).strip()


def toilet_display(toilet, benefit_year=None):
    t = _clean(toilet)
    if not t:
        return ''
    if t == 'आहे':
        y = financial_year_full(benefit_year)
        return "सन {} शौचालयाचा लाभ मिळालेला आहे.".format(y) if y else 'आहे'
    return t


def gharkul_display(gharkul, yojana=None, benefit_year=None):
    g = _clean(gharkul)
    if not g:
        return ''
    if g == 'आहे':
        yo = _clean(yojana)
        if not yo:
            return 'आहे'
        y = financial_year_full(benefit_year)
        if y:
            return "{} सन {} योजनेचा लाभ मिळाला आहे.".format(yo, y)
        return "आहे – {}".format(yo)
    return g


def register_benefit_helpers(env):
    """Jinja env मध्ये financial_year_full filter + toilet_display/gharkul_display globals."""
    env.filters['financial_year_full'] = financial_year_full
    env.globals['toilet_display'] = toilet_display
    env.globals['gharkul_display'] = gharkul_display
    return env
