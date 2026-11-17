"""क्षेत्रफळ (चौ.फु./चौ.मी.) डिस्प्ले - MASTER > नमुना ८ प्रिंट सेटिंग "Round Up All Area"
(Namuna8SettingChecklist.roundupArea, ग्रामपंचायतवार) नुसार. क्लायंटचा नियम (Nov-2026):

  - चालू (ON)  -> नेहमी वरचा पूर्ण आकडा:      598.5 -> 599, 401.04 -> 402, 1000 -> 1000
  - बंद (OFF)  -> अचूक आकडा, कमाल 2 दशांश,
                 शेवटची शून्यं नाहीत:        598.5 -> 598.5, 401.04 -> 401.04, 1000 -> 1000

नमुना-8 नोंद स्क्रीन, सर्व नमुना-8 प्रिंट्स, यादी, QR आणि नाव प्लेट - सगळीकडे फक्त हेच
वापरायचं (frontend: src/lib/areaUnits.ts मधलं formatAreaDisplay - तोच नियम).
फक्त डिस्प्लेसाठी: कर/भांडवली मूल्य याआधीच कच्च्या क्षेत्रफळावरून मोजलेले असतात,
इथे कधीच कर मोजायचा नाही. लांबी/रुंदी (मोजमाप) यातून जात नाहीत.
"""
import math
from decimal import Decimal, ROUND_HALF_UP


def get_area_round_up(db, gram_panchayat_id=None) -> bool:
    if not gram_panchayat_id:
        return False
    try:
        from namuna8 import namuna8_model
        checklist = db.query(namuna8_model.Namuna8SettingChecklist).filter(
            namuna8_model.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id
        ).first()
        return bool(checklist and checklist.roundupArea)
    except Exception:
        return False


def _two_decimals(v: float) -> float:
    # HALF_UP 2 दशांश (float च्या 0.125 -> 0.12 सारख्या बँकर्स/representation घोळाशिवाय)
    return float(Decimal(repr(float(v))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def area_value(value, round_up: bool):
    """एक क्षेत्रफळ आकडा नियमानुसार - पूर्ण आकडा असल्यास int (प्रिंटवर "1000", "1000.0" नाही),
    नाहीतर कमाल 2 दशांशाचा float (598.5, 401.04). आकडा नसेल (None/""/मजकूर) तर जसाच्या तसा."""
    if value is None or isinstance(value, bool):
        return value
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    v2 = _two_decimals(v)
    if round_up:
        # आधी 2 दशांश - float चा 1200.0000001 सारखा कचरा 1201 होऊ नये.
        return int(math.ceil(v2))
    return int(v2) if v2 == int(v2) else v2


def area_text(value, round_up: bool = None) -> str:
    """छापण्यासाठी मजकूर. round_up=None -> आकडा आधीच नियमानुसार आहे, फक्त स्वरूप (शेवटची
    शून्यं नाहीत) लावतो."""
    if value is None or value == "":
        return ""
    v = area_value(value, bool(round_up)) if round_up is not None else area_value(value, False)
    return str(v)


def jinja_area(value):
    """Jinja filter `area`: बॅकएंडने आधीच नियमानुसार केलेला आकडा फक्त स्वरूपात (598.5, 1000)."""
    if value is None or value == "":
        return ""
    v = area_value(value, False)
    return v if isinstance(v, (int, float)) else value
