"""कर रक्कम राउंडिंग - एकच शेअर्ड फंक्शन, संपूर्ण सॉफ्टवेअरमध्ये (नमुना-8 entry/print/
All Report/Excel, नमुना-9 incl. new-year creation, ९ क, ९ क2, नमुना १०, name plate,
QR, sticker) हीच वापरायची - जिथेही गणना केलेली कर रक्कम पूर्ण रुपयात आणायची असते तिथे.

MASTER > नमुना ८ संबंधी इतर सेटिंग मधल्या "कर रक्कम राउंडिंग" सेटिंगनुसार (गाव
पंचायतवार) दोन पैकी एक मोड वापरतो:
  - "ceil"    : नेहमी वरचा रुपया (जुनी/सध्याची पद्धत) - उदा. 1014.13 -> 1015   [डिफॉल्ट]
  - "half_up" : साधारण नियम - उदा. 1014.13 -> 1014, 1014.50 -> 1015
                (Decimal ROUND_HALF_UP वापरतो, पायथनच्या round() च्या बँकर्स
                राउंडिंगने नाही - त्यामुळे 0.5 नेहमी वरती जातो.)

सेटिंग सेव्ह केलेली नसेल (किंवा gram_panchayat_id कळलं नाही) तर डिफॉल्ट "ceil" वापरतो
- म्हणजे सेटिंग न बदलल्यास कुठलंही वर्तन बदलत नाही.
"""
import math
from decimal import Decimal, ROUND_HALF_UP

DEFAULT_MODE = "ceil"


def get_tax_rounding_mode(db, gram_panchayat_id=None) -> str:
    if not gram_panchayat_id:
        return DEFAULT_MODE
    try:
        from namuna8 import namuna8_model
        obj = db.query(namuna8_model.Namuna8DropdownAddSettings).filter(
            namuna8_model.Namuna8DropdownAddSettings.gram_panchayat_id == gram_panchayat_id
        ).first()
        if obj and getattr(obj, 'taxRoundingMode', None):
            return obj.taxRoundingMode
    except Exception:
        pass
    return DEFAULT_MODE


def round_tax_amount(value, db, gram_panchayat_id=None) -> int:
    mode = get_tax_rounding_mode(db, gram_panchayat_id)
    if mode == "half_up":
        return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return math.ceil(value)
