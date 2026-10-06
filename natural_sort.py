# मालमत्ता क्रमांक साठी नैसर्गिक क्रम (natural sort) - जसं "32, 32/1, 32/2, 33" असं
# यायला हवं, "id" किंवा साध्या टेक्स्ट सॉर्टने नाही. हे frontend मधल्या
# compareMalmattaKramank (Namuna8.tsx, SEARCH DATA यादीसाठी वापरलेलं) शी तंतोतंत
# जुळणारं पोर्ट आहे, जेणेकरून स्क्रीन आणि प्रिंट/एक्सपोर्ट सगळीकडे एकसारखाच क्रम दिसेल.
#
# कुठेही मालमत्ता क्रमांकानुसार यादी दाखवायची/छापायची असेल तिथे इथूनच import करून
# वापरावं - लॉजिकची दुसरी कॉपी बनवू नये.

import re
from functools import cmp_to_key

# मालमत्ता क्रमांक कधी कधी आकड्याऐवजी मराठी शब्दात लिहिलेला असतो (उदा. "सहा" ऐवजी 6).
# 1-100 च्या नेहमीच्या शुद्धलेखनाला त्याच्या किमतीशी जोडतो.
MARATHI_NUMBER_WORDS = {
    "एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5,
    "सहा": 6, "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10,
    "अकरा": 11, "बारा": 12, "तेरा": 13, "चौदा": 14, "पंधरा": 15,
    "सोळा": 16, "सतरा": 17, "अठरा": 18, "एकोणीस": 19, "वीस": 20,
    "एकवीस": 21, "बावीस": 22, "तेवीस": 23, "चोवीस": 24, "पंचवीस": 25,
    "सव्वीस": 26, "सत्तावीस": 27, "अठ्ठावीस": 28, "एकोणतीस": 29, "तीस": 30,
    "एकतीस": 31, "बत्तीस": 32, "तेहेतीस": 33, "तेहतीस": 33, "चौतीस": 34, "पस्तीस": 35,
    "छत्तीस": 36, "सदतीस": 37, "अडतीस": 38, "एकोणचाळीस": 39, "चाळीस": 40,
    "एकेचाळीस": 41, "बेचाळीस": 42, "त्रेचाळीस": 43, "चव्वेचाळीस": 44, "पंचेचाळीस": 45,
    "सेहेचाळीस": 46, "शेहेचाळीस": 46, "सत्तेचाळीस": 47, "अठ्ठेचाळीस": 48, "एकोणपन्नास": 49, "पन्नास": 50,
    "एक्कावन्न": 51, "बावन्न": 52, "त्रेपन्न": 53, "चोपन्न": 54, "पंचावन्न": 55,
    "छप्पन्न": 56, "सत्तावन्न": 57, "अठ्ठावन्न": 58, "एकोणसाठ": 59, "साठ": 60,
    "एकसष्ठ": 61, "बासष्ठ": 62, "त्रेसष्ठ": 63, "चौसष्ठ": 64, "पासष्ठ": 65,
    "सहासष्ठ": 66, "सदुसष्ठ": 67, "अडुसष्ठ": 68, "एकोणसत्तर": 69, "सत्तर": 70,
    "एक्काहत्तर": 71, "बाहत्तर": 72, "त्र्याहत्तर": 73, "चौऱ्याहत्तर": 74, "पंचाहत्तर": 75,
    "शहात्तर": 76, "सत्याहत्तर": 77, "अठ्ठ्याहत्तर": 78, "एकोणऐंशी": 79, "ऐंशी": 80,
    "एक्क्याऐंशी": 81, "ब्याऐंशी": 82, "त्र्याऐंशी": 83, "चौऱ्याऐंशी": 84, "पंच्याऐंशी": 85,
    "शहाऐंशी": 86, "सत्याऐंशी": 87, "अठ्ठ्याऐंशी": 88, "एकोणनव्वद": 89, "नव्वद": 90,
    "एक्क्याण्णव": 91, "ब्याण्णव": 92, "त्र्याण्णव": 93, "चौऱ्याण्णव": 94, "पंच्याण्णव": 95,
    "शहाण्णव": 96, "सत्त्याण्णव": 97, "अठ्ठ्याण्णव": 98, "नव्याण्णव": 99, "शंभर": 100,
    "अठेचाळीस": 48,  # "अठ्ठेचाळीस" (48) चं सर्रास टाईप होणारं शुद्धलेखन (एक ठ् कमी)
}

# शंभरच्या पटीतले शब्द (उदा. "तीनशे" = 300) - "तीनशे अठ्ठेचाळीस" (348) सारख्या संयुक्त
# संख्यांसाठी "शे"-शब्द + उरलेला MARATHI_NUMBER_WORDS मधला शब्द बेरीज करून वापरतो.
MARATHI_HUNDREDS_WORDS = {
    "शंभर": 100, "दोनशे": 200, "तीनशे": 300, "चारशे": 400, "पाचशे": 500,
    "सहाशे": 600, "सातशे": 700, "आठशे": 800, "नऊशे": 900,
}

ENGLISH_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
ENGLISH_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_DEVANAGARI_DIGIT_TRANSLATION = str.maketrans("०१२३४५६७८९", "0123456789")
_DIGITS_ONLY = re.compile(r"^\d+$")


def _devanagari_digits_to_ascii(value: str) -> str:
    return value.translate(_DEVANAGARI_DIGIT_TRANSLATION)


def _marathi_words_to_number_compositional(segment: str):
    words = [w for w in re.split(r"[\s-]+", _devanagari_digits_to_ascii(segment).strip()) if w]
    if not words:
        return None
    total = 0
    matched = False
    for w in words:
        if w in MARATHI_HUNDREDS_WORDS:
            total += MARATHI_HUNDREDS_WORDS[w]
            matched = True
        elif w in MARATHI_NUMBER_WORDS:
            total += MARATHI_NUMBER_WORDS[w]
            matched = True
        else:
            return None
    return total if matched else None


def _marathi_words_to_digits(value: str) -> str:
    tokens = re.split(r"([\/\-\s]+)", value)
    out = []
    for token in tokens:
        trimmed = token.strip()
        if trimmed and trimmed in MARATHI_NUMBER_WORDS:
            out.append(str(MARATHI_NUMBER_WORDS[trimmed]))
        else:
            out.append(token)
    return "".join(out)


def _english_words_to_number(segment: str):
    words = [w for w in re.split(r"[\s-]+", segment.lower().strip()) if w]
    if not words:
        return None
    total = 0
    matched = False
    for w in words:
        if w in ENGLISH_TENS:
            total += ENGLISH_TENS[w]
            matched = True
        elif w in ENGLISH_ONES:
            total += ENGLISH_ONES[w]
            matched = True
        elif w == "hundred":
            total = (total or 1) * 100
            matched = True
        else:
            return None
    return total if matched else None


def _segment_to_number(segment: str):
    trimmed = segment.strip()
    if _DIGITS_ONLY.match(trimmed):
        return int(trimmed)
    marathi_converted = _marathi_words_to_digits(_devanagari_digits_to_ascii(trimmed))
    if _DIGITS_ONLY.match(marathi_converted):
        return int(marathi_converted)
    marathi_compositional = _marathi_words_to_number_compositional(trimmed)
    if marathi_compositional is not None:
        return marathi_compositional
    return _english_words_to_number(trimmed)


def compare_malmatta_kramank(a, b) -> int:
    """Natural-order comparator for मालमत्ता क्रमांक values like "80", "80/1", "80/2",
    "81" (digits, Marathi words, or English words) - compares numeric segments split
    on "/" or "-" in order, so they sort by value, not text. Mirrors the frontend's
    compareMalmattaKramank (Namuna8.tsx) exactly, including its tie-break fallback."""

    def to_parts(v):
        s = str(v) if v is not None else ""
        return [
            seg_num if (seg_num := _segment_to_number(seg)) is not None else -1
            for seg in re.split(r"[\/\-]", s)
        ]

    pa = to_parts(a)
    pb = to_parts(b)
    length = max(len(pa), len(pb))
    for i in range(length):
        na = pa[i] if i < len(pa) else -1
        nb = pb[i] if i < len(pb) else -1
        if na != nb:
            return -1 if na < nb else 1
    sa = str(a) if a is not None else ""
    sb = str(b) if b is not None else ""
    if sa == sb:
        return 0
    return -1 if sa < sb else 1


def malmatta_kramank_sort_key(value):
    """Use as sorted(items, key=lambda i: malmatta_kramank_sort_key(i.malmattaKramank))."""
    return cmp_to_key(compare_malmatta_kramank)(value)
