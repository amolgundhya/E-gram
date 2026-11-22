"""क्षेत्रफळ (चौ.फु./चौ.मी.) डिस्प्ले. क्लायंटचा नियम (22-Nov-2026): क्षेत्रफळ कधीच पूर्ण
आकड्यात गोल नाही - नेहमी 2 दशांश (HALF_UP). MASTER "Round Up All Area" आता फक्त कर
राउंडिंगसाठी (Utility/tax_rounding.py), क्षेत्रफळावर परिणाम नाही (round_up arg दुर्लक्षित).
नमुना-8 प्रिंट्समध्ये 2 दशांश स्थिर स्वरूपात: 338 -> "338.00" (jinja_area / AreaNumber).

नमुना-8 नोंद स्क्रीन, सर्व नमुना-8 प्रिंट्स, यादी, QR आणि नाव प्लेट - सगळीकडे फक्त हेच
वापरायचं (frontend: src/lib/areaUnits.ts मधलं formatAreaDisplay - तोच नियम).
फक्त डिस्प्लेसाठी: कर/भांडवली मूल्य Utility.area_units.area_sqm_for_tax (तोच 2 दशांशाचा
चौ.मी.) वरून मोजलेले असतात, इथे कधीच कर मोजायचा नाही. लांबी/रुंदी (मोजमाप) यातून जात नाहीत.
"""
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
    return int(v2) if v2 == int(v2) else v2


def area_text(value, round_up: bool = None) -> str:
    """छापण्यासाठी मजकूर. round_up=None -> आकडा आधीच नियमानुसार आहे, फक्त स्वरूप (शेवटची
    शून्यं नाहीत) लावतो."""
    if value is None or value == "":
        return ""
    v = area_value(value, bool(round_up)) if round_up is not None else area_value(value, False)
    return str(v)


def area_2dp_text(value):
    """नमुना-8 प्रिंटसाठी: नेहमी 2 दशांश ("338.00", "23.49"). आकडा नसेल तर जसाच्या तसा."""
    if value is None or value == "" or isinstance(value, bool):
        return "" if value is None else value
    try:
        return f"{_two_decimals(float(value)):.2f}"
    except (TypeError, ValueError):
        return value


class AreaNumber(float):
    """नमुना-8 प्रिंट context मधला क्षेत्रफळ आकडा: गणित/तुलना float सारखीच, पण छापताना
    (str) नेहमी 2 दशांश - templates मध्ये |area न लावलेल्या ठिकाणीही "338.00"."""
    def __str__(self):
        return f"{float(self):.2f}"


AREA_KEYS = {
    "total_arearinfoot", "totalareainmeters", "totalArea", "totalAreaSqFt",
    "totalkhalijagaareainfoot", "totalkhalijagaareainmeters",
    "totalconstructionareainfoot", "totalconstructionareainmeter", "areaSqft", "areaSqm",
}


def wrap_area_numbers(obj, in_khali: bool = False):
    """प्रिंट context मधल्या क्षेत्रफळ keys (आणि khaliJaga मधली 'length' = खाली जागेचं
    क्षेत्रफळ) AreaNumber मध्ये. नवीन dict/list परत (मूळ बदलत नाही)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out[k] = wrap_area_numbers(v, in_khali=(k == "khaliJaga"))
            elif (k in AREA_KEYS or (in_khali and k == "length")) and isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = AreaNumber(_two_decimals(v))
            else:
                out[k] = v
        return out
    if isinstance(obj, list):
        return [wrap_area_numbers(i, in_khali=in_khali) for i in obj]
    return obj


def jinja_area(value):
    """Jinja filter `area` (नमुना-8 प्रिंट): नेहमी 2 दशांश ("338.00")."""
    return area_2dp_text(value)
