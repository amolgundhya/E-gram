"""कर रक्कम राउंडिंग - एकच शेअर्ड फंक्शन, संपूर्ण सॉफ्टवेअरमध्ये (नमुना-8 entry/print/
All Report/Excel, नमुना-9 incl. new-year creation, ९ क, ९ क2, नमुना १०, name plate,
QR, sticker) हीच वापरायची - जिथेही गणना केलेली कर रक्कम पूर्ण रुपयात आणायची असते तिथे.

वेगळं "कर रक्कम राउंडिंग" सेटिंग नाही (ते काढलं) - MASTER > नमुना ८ प्रिंट सेटिंग
मधल्या आधीपासूनच्या "Round Up All Area" (Namuna8SettingChecklist.roundupArea,
गाव पंचायतवार) चेकबॉक्सनुसारच ठरतो:
  - टिक केलेला   -> "ceil" (नाव जुनं) : क्लायंट 23-Nov-2026 - आता ceil नाही, साधारण
                राउंडिंग - उदा. 52.15 -> 52, 52.50 -> 53, 52.51 -> 53, 525.19 -> 525
  - टिक नसलेला  -> "half_up" : साधारण नियम - उदा. 1014.13 -> 1014, 1014.50 -> 1015
दोन्हीमध्ये Decimal ROUND_HALF_UP (round_half_up) - पायथनच्या round() च्या बँकर्स
राउंडिंगने नाही (round(52.5) = 52) - त्यामुळे 0.5 नेहमी वरती जातो.

gram_panchayat_id कळलं नाही किंवा चेकलिस्ट रो सापडला नाही तर डिफॉल्ट "half_up".
भांडवली मूल्य (capital value) या फंक्शनमधून कधीच जात नाही - ते नेहमी अचूक, फक्त
2 दशांश स्थळांपर्यंत ठेवायचं (वेगळीकडे round(value, 2) ने), इथे राउंड करायचं नाही.
"""
from decimal import Decimal, ROUND_HALF_UP

DEFAULT_MODE = "half_up"


def get_tax_rounding_mode(db, gram_panchayat_id=None) -> str:
    if not gram_panchayat_id:
        return DEFAULT_MODE
    try:
        from namuna8 import namuna8_model
        checklist = db.query(namuna8_model.Namuna8SettingChecklist).filter(
            namuna8_model.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id
        ).first()
        if checklist and checklist.roundupArea:
            return "ceil"
    except Exception:
        pass
    return DEFAULT_MODE


def round_half_up(value) -> int:
    """साधारण राउंडिंग: .5 व त्यावर -> वरचा रुपया, खाली -> खालचा (52.5 -> 53)."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_tax_amount(value, db, gram_panchayat_id=None) -> int:
    # "Round Up All Area" टिक असो वा नसो - कर नेहमी साधारण राउंडिंगने (23-Nov-2026,
    # आधी टिक केल्यावर math.ceil होतं: 52.15 -> 53).
    return round_half_up(value)
