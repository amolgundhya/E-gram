"""खाली जागा - क्षेत्रफळ, भांडवली मूल्य व कर. नमुना-8 (नोंद/print/QR/bulk list) आणि नमुना-9
(screen, current_year_sync, print) सगळे हेच एक फंक्शन वापरतात, म्हणजे दोन्हीकडे खाली जागा
आणि एकूण घरपट्टी नेहमी सारखीच.

नियम (क्लायंट Nov-2026): खाली जागा = एकूण क्षेत्रफळ - फक्त तळमजल्याचं (मजला "तळमजला"
किंवा रिकामा) बांधकाम. तळमजला/रिकामी रो असेल तर पहिला/दुसरा मजला खाली जागा कमी करत नाही.
तळमजला/रिकामी रो नसून फक्त वरचे मजले असतील (उदा. प्लॉट 862 + फक्त पहिला मजला 589) तर
सगळ्यात मोठ्या एका मजल्याचं क्षेत्रफळ (इमारतीचा ठसा) वजा - सगळ्या मजल्यांची बेरीज नाही
(क्लायंट 17-Nov-2026: 862 - 589 = 273). एका मजल्याची अनेक रो असतील तर त्या मजल्याची बेरीज
हा त्या मजल्याचा आकार. एकूण जागा नसलेले फ्लॅट: खाली जागा 0 (बदल नाही). वजाबाकी प्लॉटच्याच
एककात (areaUnit) गोल न करता; बांधकाम वेगळ्या एककात (constructionAreaUnit) असेल तरच एकदा
रूपांतर. भांडवली मूल्यासाठी चौ.मी. क्षेत्रफळ पूर्ण अचूक (एकूण - तळमजला गोल न करता, मग
÷10.764 - Utility.area_units.area_sqm_for_tax); दाखवायचं चौ.मी. (khali_sqm) 2 दशांश.
"Round Up All Area" चालू असेल तर भांडवली मूल्यासाठी खाली जागेचं चौ.मी. सुद्धा वरचा पूर्ण आकडा
(क्लायंट 22-Nov-2026) - प्रिंटवर दिसतो तोच.
"""
from Utility.area_units import convert_area, to_sqft, area_sqm_for_tax, round_sqm, sqft_to_sqm

GROUND_FLOORS = ("", "तळमजला")


def is_ground_floor(construction) -> bool:
    return (getattr(construction, "floor", None) or "").strip() in GROUND_FLOORS


def _is_khali_type_row(construction) -> bool:
    ct = getattr(construction, "construction_type", None)
    return (getattr(ct, "name", None) or "").strip().startswith("खाली जागा")


def has_vacant_land(prop) -> bool:
    return getattr(prop, "vacantLandType", None) not in (None, "", "null")


def _largest_upper_floor_area(constructions):
    """तळमजला/रिकामी रो नसताना: मजल्यानुसार क्षेत्रफळांची बेरीज, त्यातला सगळ्यात मोठा मजला
    (constructionAreaUnit मध्ये). "खाली जागा" प्रकाराच्या रो इमारतीचा भाग नाहीत, म्हणून वगळल्या."""
    per_floor = {}
    for c in constructions:
        if _is_khali_type_row(c):
            continue
        floor = (getattr(c, "floor", None) or "").strip()
        per_floor[floor] = per_floor.get(floor, 0) + (c.length or 0) * (c.width or 0)
    return max(per_floor.values(), default=0)


def _round_up_from_round_tax(round_tax) -> bool:
    """round_tax हे round_tax_amount (किंवा cached आवृत्ती) - ते "Round Up All Area" नुसारच ceil /
    half_up करतं (Utility/tax_rounding.py). 0.4 -> 1 म्हणजे ceil = सेटिंग चालू. त्यामुळे सगळ्या
    callers ना नवीन parameter द्यावा लागत नाही आणि दोन्ही नेहमी एकाच सेटिंगवरून."""
    try:
        return round_tax(0.4) == 1
    except Exception:
        return False


def khali_jaga(prop, constructions, khali_construction_type, round_tax, area_round_up=None):
    """खाली जागेची सर्व मूल्यं dict मध्ये. khali_construction_type: vacantLandType नावाचा
    ConstructionType (नसेल तर None -> कर 0). round_tax: कर रक्कम पूर्ण रुपयात आणणारं फंक्शन
    (round_tax_amount / त्याचीच cached आवृत्ती). area_round_up: "Round Up All Area" (None ->
    round_tax वरून ओळखतो)."""
    if area_round_up is None:
        area_round_up = _round_up_from_round_tax(round_tax)
    unit = getattr(prop, "areaUnit", None) or "sqft"
    unit = "sqm" if unit == "sqm" else "sqft"
    cunit = getattr(prop, "constructionAreaUnit", None) or unit
    cunit = "sqm" if cunit == "sqm" else "sqft"
    total_native = (getattr(prop, "totalArea", None) or 0) if unit == "sqm" else (getattr(prop, "totalAreaSqFt", None) or 0)

    ground = [c for c in constructions if is_ground_floor(c)]
    used_raw = sum((c.length or 0) * (c.width or 0) for c in ground)
    # खरी (खाली-जागा-प्रकार नसलेली) तळमजला रो नसेल तर वरच्या सगळ्यात मोठ्या मजल्याचा ठसा
    # सुद्धा वजा. तळमजल्यावर फक्त स्वतः जोडलेली "खाली जागा" रो असेल (उदा. प्लॉट 862 + पहिला
    # मजला 589 + खाली जागा रो 273) तर ती "तळमजला" धरून जुना नियम लागू होऊ नये.
    if not any(not _is_khali_type_row(c) for c in ground):
        used_raw += _largest_upper_floor_area(constructions)
    used_native = convert_area(used_raw, cunit, unit)
    khali_native = max(total_native - used_native, 0)

    # बांधकाम तक्त्यात स्वतः टाकलेली "खाली जागा" प्रकाराची (तळमजला) रो वर "वापरलेली" धरली आहे
    # (तिचा कर तिच्या रो वरच), पण दाखवताना ती खुली जागाच - म्हणून display मध्ये परत जोडतो.
    khali_rows_native = convert_area(sum((c.length or 0) * (c.width or 0) for c in ground if _is_khali_type_row(c)), cunit, unit)
    display_native = khali_native + khali_rows_native

    khali_sqft = round(to_sqft(khali_native, unit), 2)
    # दाखवण्यासाठी 2 दशांश; भांडवली मूल्य पूर्ण अचूक क्षेत्रफळावरून (क्लायंट 20-Nov-2026).
    khali_sqm = round_sqm(khali_native) if unit == "sqm" else sqft_to_sqm(khali_native)
    khali_sqm_exact = area_sqm_for_tax(khali_native, unit, area_round_up)
    capital_value, house_tax, rate = 0, 0, 0
    if khali_native > 0 and khali_construction_type is not None:
        capital_value = round(khali_sqm_exact * (getattr(khali_construction_type, "annualLandValueRate", 1) or 0), 2)
        rate = getattr(khali_construction_type, "rate", 0) or 0
        house_tax = round_tax((rate / 1000) * capital_value)
    return {
        "unit": unit,
        "khali_native": khali_native,
        "khali_sqft": khali_sqft,
        "khali_sqm": khali_sqm,
        "display_sqft": round(to_sqft(display_native, unit), 2),
        "display_sqm": round_sqm(display_native) if unit == "sqm" else sqft_to_sqm(display_native),
        "capital_value": capital_value,
        "house_tax": house_tax,
        "rate": rate,
    }


def property_house_tax(prop, constructions, khali_construction_type, round_tax):
    """एकूण घरपट्टी = प्रत्येक बांधकाम रो चा जतन केलेला houseTax + खाली जागा कर.
    नमुना-8 total आणि नमुना-9 चालू घरपट्टी दोन्ही याच फंक्शनमधून."""
    if bool(getattr(prop, "karLaguNahi", False)):
        return 0
    total = sum((c.houseTax or 0) for c in constructions)
    if has_vacant_land(prop):
        total += khali_jaga(prop, constructions, khali_construction_type, round_tax)["house_tax"]
    return total
