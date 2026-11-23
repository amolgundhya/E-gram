"""मालमत्तेच्या सर्व QR कोड्ससाठी (नमुना-8 प्रिंट QR, नमुना-9/house QR, कचरा
sticker QR, नाव प्लेट QR) समान, वाचनीय plain-text मजकूर तयार करतो - JSON ऐवजी,
जेणेकरून कोणत्याही सामान्य QR स्कॅनर अ‍ॅपने स्कॅन केल्यावर माणसाला थेट वाचता यावं.

सर्व 4 ठिकाणी हाच एक function वापरायचा, जेणेकरून मजकुराचं स्वरूप कायम सुसंगत राहील.
"""
from Utility.area_display import area_text


# मालकाचे नाव QR मजकुरात दाखवायचं की नाही (Windows 10 प्रमाणे: होय).
QR_INCLUDE_OWNER_NAME = True


def _unit_label(unit: str) -> str:
    return "चौ.मी." if (unit or "").strip() == "sqm" else "चौ.फु."


def _fmt_num(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    if v == int(v):
        return str(int(v))
    return ("%.2f" % v).rstrip("0").rstrip(".")


def build_gp_heading(gp_name, taluka_name, district_name, parent_gp_name=None) -> str:
    gp_name = gp_name or ""
    taluka_name = taluka_name or ""
    district_name = district_name or ""
    if parent_gp_name:
        return f"ग्रामपंचायत {parent_gp_name}, गट ग्रा.पं. {gp_name}, ता. {taluka_name}, जि. {district_name}"
    return f"ग्रा.पं. {gp_name}, ता. {taluka_name}, जि. {district_name}"


def _short_construction_name(name, max_len: int = 18) -> str:
    name = (name or "").strip()
    if len(name) <= max_len:
        return name
    return name[: max_len - 1].rstrip() + "…"


def build_area_lines(record: dict, decimals: int = 2, short_names: bool = True, include_type: bool = True) -> list:
    """एकूण क्षेत्रफळ / बांधकाम (प्रत्येकी एक ओळ) / खाली जागा च्या ओळी - कचरा sticker
    आणि नाव प्लेट दोन्ही हेच वापरतात, त्यामुळे कधीही एकमेकांपासून वेगळ्या दिसणार नाहीत.
    0 असलेल्या ओळी वगळतो. include_type=False केल्यास बांधकाम-प्रकाराचं नाव (कंसातलं)
    वगळतो - फक्त QR मजकूर आणखी लहान करण्यासाठी (इतर कुठेही वापरत नाही, तिथे
    include_type=True हाच राहतो)."""
    unit = record.get("areaUnit") or "sqft"
    construction_unit = record.get("constructionAreaUnit") or unit
    # क्षेत्रफळ MASTER "Round Up All Area" नुसार (Utility/area_display): चालू = वरचा पूर्ण
    # आकडा, बंद = अचूक (कमाल 2 दशांश, शेवटची शून्यं नाहीत). record मधले एकूण/खाली जागा
    # आकडे बॅकएंडने आधीच याच नियमाने केलेले असतात; areaRoundUp नसेल तर जसे आहेत तसे.
    # (decimals हा जुना पॅरामीटर आता वापरत नाही - सगळीकडे एकच नियम.)
    round_up = record.get("areaRoundUp")
    unit_lbl = _unit_label(unit)
    c_unit_lbl = _unit_label(construction_unit)

    east = record.get("areaEast") or 0
    west = record.get("areaWest") or 0
    north = record.get("areaNorth") or 0
    south = record.get("areaSouth") or 0
    avg_length = round((east + west) / 2, 2) if (east or west) else 0
    avg_width = round((north + south) / 2, 2) if (north or south) else 0
    total_area = record.get("totalareainmeters") if unit == "sqm" else record.get("total_arearinfoot")

    lines = []
    if total_area:
        total_area_fmt = area_text(total_area, round_up)
        if avg_length and avg_width:
            lines.append(f"एकूण क्षेत्रफळ : {_fmt_num(avg_length)} X {_fmt_num(avg_width)} = {total_area_fmt} {unit_lbl}")
        else:
            lines.append(f"एकूण क्षेत्रफळ : {total_area_fmt} {unit_lbl}")

    for c in (record.get("constructionType") or []):
        c_type_raw = (c.get("type") or "").strip()
        length = c.get("length") or 0
        width = c.get("width") or 0
        # बॅकएंडने नियमानुसार केलेलं बांधकाम क्षेत्रफळ (areaSqm/areaSqft) असल्यास तेच.
        area_key = "areaSqm" if construction_unit == "sqm" else "areaSqft"
        area = c.get(area_key) if c.get(area_key) not in (None, "") else round(length * width, 2)
        if not c_type_raw or c_type_raw.startswith("खाली जागा"):
            # खाली-जागा-प्रकारची construction रो "बांधकाम" म्हणून दाखवायची नाही - ती
            # जागा get_property_record मध्येच खाली जागाच्या एकूण बेरजेत आधी धरलेली
            # असते (खाली khaliJaga[0] मधून तेच वाचतो), इथे परत बेरीज करायची नाही
            # (दोनदा मोजली जाईल).
            continue
        if not area:
            continue
        area_fmt = area_text(area, round_up)
        if include_type:
            c_type = _short_construction_name(c_type_raw) if short_names else c_type_raw
            lines.append(f"बांधकाम : {_fmt_num(length)} X {_fmt_num(width)} = {area_fmt} {c_unit_lbl} ({c_type})")
        else:
            lines.append(f"बांधकाम : {_fmt_num(length)} X {_fmt_num(width)} = {area_fmt} {c_unit_lbl}")

    # खाली जागा - get_property_record आधीच (auto-computed उरलेलं + खाली-जागा-प्रकारच्या
    # construction रो चं क्षेत्रफळ) एकत्र करून totalkhalijagaareain* मध्ये देतो, तेच
    # थेट वापरतो.
    khali = record.get("khaliJaga") or []
    if khali:
        khali_area = khali[0].get("totalkhalijagaareainmeters") if unit == "sqm" else khali[0].get("totalkhalijagaareainfoot")
        khali_area = khali_area or 0.0
        if khali_area:
            khali_fmt = area_text(khali_area, round_up)
            lines.append(f"खाली जागा : {khali_fmt} {unit_lbl}")

    return lines


def _mobile_number(record: dict) -> str:
    """मोबाईल क्र. - रिकामा / फक्त शून्यं ("0", "००००") असेल तर "" """
    mobile = str(record.get("mobileNumber") or "").strip()
    if not mobile.translate(str.maketrans('०१२३४५६७८९', '0123456789')).strip("0 "):
        return ""
    return mobile


def build_contact_boundary_lines(record: dict) -> list:
    """मोबाईल क्र. आणि चतुःसीमा (दिशा: पूर्व/पश्चिम/उत्तर/दक्षिण) च्या ओळी - रिकाम्या वगळतो.
    नाव प्लेटवर ही माहिती छापत नाही, मोठ्या QR स्कॅन केल्यावरच दिसते (क्लायंट विनंती,
    नोव्हें 2026)."""
    lines = []
    mobile = _mobile_number(record)
    if mobile:
        lines.append(f"मोबाईल : {mobile}")
    for label, key in (("पूर्व", "boundaryEast"), ("पश्चिम", "boundaryWest"),
                       ("उत्तर", "boundaryNorth"), ("दक्षिण", "boundarySouth")):
        value = str(record.get(key) or "").strip()
        if value:
            lines.append(f"{label} : {value}")
    return lines


def build_construction_type_lines(record: dict) -> list:
    """प्रत्येक बांधकाम रो साठी "बांधकाम प्रकार : <प्रकार> (<मजला>)" ओळ - "खाली जागा"
    प्रकारच्या रो आणि रिकामा प्रकार वगळतो; मजला रिकामा असेल तर कंस नाही. नाव प्लेटवर
    छापत नाही, फक्त मोठ्या QR स्कॅन केल्यावर दिसते (क्लायंट, 19-नोव्हें 2026)."""
    lines = []
    for c in (record.get("constructionType") or []):
        c_type = (c.get("type") or "").strip()
        if not c_type or c_type.startswith("खाली जागा"):
            continue
        floor = str(c.get("floor") or "").strip()
        lines.append(f"बांधकाम प्रकार : {c_type} ({floor})" if floor else f"बांधकाम प्रकार : {c_type}")
    return lines


def build_property_qr_text(record: dict, parent_gp_name: str = None, year_label: str = None,
                           include_contact: bool = False) -> str:
    """record: get_property_record() / property_records_by_village() स्टाईलचा dict
    (srNo, propertyNumber, ownerName, occupantName, gramPanchayat, taluka, jilha,
    areaEast/West/North/South, total_arearinfoot, totalareainmeters, areaUnit,
    constructionAreaUnit, constructionType[], khaliJaga[], totalHouseTax,
    lightingTax, healthTax, sapanikar, vpanikar, cleaningTax, totaltax).

    Devanagari अक्षरं UTF-8 मध्ये प्रत्येकी ~3 बाईट्स घेतात, त्यामुळे मजकूर जरा जास्त
    लांब झाला तरी QR version खूप वाढतो (आणि छापलेल्या छोट्या बॉक्समध्ये स्कॅन करणं
    अवघड होतं) - म्हणून लेबल्स शक्य तितकी लहान ठेवतो, 0/रिकाम्या कराच्या ओळी (एकूण
    कर सोडून) वगळतो, बांधकाम-प्रकाराचं नाव (कंसातलं) वगळतो, आणि ग्रा.पं./ता./जि.
    मथळा ओळ वगळतो (ती कागदावर आधीच छापलेली असते - parent_gp_name इथे यामुळेच
    वापरत नाही, पण इतर कॉलर्सशी सुसंगत राहण्यासाठी parameter तसाच ठेवलाय).
    include_contact=True (फक्त नाव प्लेट): मोबाईल क्र. व चतुःसीमा ओळी, आणि बांधकाम
    ओळींनंतर प्रत्येक बांधकाम रो चा "बांधकाम प्रकार : <प्रकार> (<मजला>)" ओळ जोडतो."""
    lines = [
        f"अ.क्र. : {record.get('srNo') or ''}",
        f"मालमत्ता क्र. : {record.get('propertyNumber') or ''}",
    ]
    if QR_INCLUDE_OWNER_NAME:
        lines.append(f"मालक : {record.get('ownerName') or ''}")
    lines.append(f"भोगवटदार : {record.get('occupantName') or 'स्वतः'}")
    if include_contact:
        lines.extend(build_contact_boundary_lines(record))
    lines.extend(build_area_lines(record, include_type=False))
    if include_contact:
        lines.extend(build_construction_type_lines(record))
    if year_label:
        lines.append(f"साल : {year_label}")

    tax_items = [
        ("घरपट्टी", record.get("totalHouseTax")),
        ("दिवाबत्ती", record.get("lightingTax")),
        ("आरोग्य", record.get("healthTax")),
        ("सा.पाणी", record.get("sapanikar")),
        ("वि.पाणी", record.get("vpanikar")),
        ("सफाई", record.get("cleaningTax")),
    ]
    if include_contact:
        # नाव प्लेट: शौचालय कर (> 0 असल्यास) - ओळींची बेरीज = एकूण कर (क्लायंट, नोव्हें 2026)
        tax_items.append(("शौचालय कर", record.get("toiletTax")))
    for label, amount in tax_items:
        if _fmt_num(amount) != "0":
            lines.append(f"{label} : {_fmt_num(amount)}")
    lines.append(f"एकूण कर : {_fmt_num(record.get('totaltax'))}")

    return "\n".join(lines)


def build_property_qr_text_short(record: dict) -> str:
    """रिपोर्ट्सवरचा "मालमत्ता QR" (नमुना-8 प्रिंट्स, 9क, 9क-2, लेख, लेख-2, पावती -
    /namuna8/property_qrcode व मालमत्ता सेव्ह/अपडेट). क्लायंटचं स्वरूप (23-नोव्हें 2026),
    रिकामी ओळ वगळतो (0 कर सुद्धा; एकूण कर नेहमी):
        अ.क्र. : 8
        मालमत्ता क्र. : 349
        मालक : <नाव>
        भोगवट : <भोगवटदार>
        एकूण क्षेत्रफळ : 40 X 33 = 1320.00 चौ.फु.
        बांधकाम : 15 X 33 = 495.00 चौ.फु.      (प्रत्येक बांधकाम रो ची एक ओळ)
        खाली जागा : 825.00 चौ.फु.
        साल : 2026-2027
        घरपट्टी / दिवाबत्ती / आरोग्य / सा.पाणी : <रक्कम>
        एकूण कर : 705
    क्षेत्रफळ 2 दशांश (area_2dp_text), मोजमाप शेवटच्या शून्यांशिवाय. नाव प्लेट QR वेगळा
    (build_property_qr_text, include_contact=True - पूर्ण मजकूर)."""
    from datetime import datetime
    from Utility.area_display import area_2dp_text

    unit = record.get("areaUnit") or "sqft"
    c_unit = record.get("constructionAreaUnit") or unit
    unit_lbl, c_unit_lbl = _unit_label(unit), _unit_label(c_unit)
    lines = []

    def add(label, value):
        value = str(value if value is not None else "").strip()
        if value:
            lines.append(f"{label} : {value}")

    add("अ.क्र.", record.get("srNo"))
    add("मालमत्ता क्र.", record.get("propertyNumber"))
    add("मालक", record.get("ownerName"))
    add("भोगवट", record.get("occupantName"))

    east, west = record.get("areaEast") or 0, record.get("areaWest") or 0
    north, south = record.get("areaNorth") or 0, record.get("areaSouth") or 0
    avg_l = round((east + west) / 2, 2) if (east or west) else 0
    avg_w = round((north + south) / 2, 2) if (north or south) else 0
    total = record.get("totalareainmeters") if unit == "sqm" else record.get("total_arearinfoot")
    if total:
        size = f"{_fmt_num(avg_l)} X {_fmt_num(avg_w)} = " if (avg_l and avg_w) else ""
        lines.append(f"एकूण क्षेत्रफळ : {size}{area_2dp_text(total)} {unit_lbl}")

    area_key = "areaSqm" if c_unit == "sqm" else "areaSqft"
    for c in (record.get("constructionType") or []):
        c_type = (c.get("type") or "").strip()
        if not c_type or c_type.startswith("खाली जागा"):
            continue   # खाली-जागा रो खाली जागाच्या बेरजेत आधीच (build_area_lines प्रमाणे)
        length, width = c.get("length") or 0, c.get("width") or 0
        area = c.get(area_key) if c.get(area_key) not in (None, "") else round(length * width, 2)
        if area:
            lines.append(f"बांधकाम : {_fmt_num(length)} X {_fmt_num(width)} = {area_2dp_text(area)} {c_unit_lbl}")

    khali = record.get("khaliJaga") or []
    if khali:
        k = khali[0].get("totalkhalijagaareainmeters") if unit == "sqm" else khali[0].get("totalkhalijagaareainfoot")
        if k:
            lines.append(f"खाली जागा : {area_2dp_text(k)} {unit_lbl}")

    year = datetime.now().year
    lines.append(f"साल : {year}-{year + 1}")
    for label, key in (("घरपट्टी", "totalHouseTax"), ("दिवाबत्ती", "lightingTax"),
                       ("आरोग्य", "healthTax"), ("सा.पाणी", "sapanikar")):
        if _fmt_num(record.get(key)) != "0":
            lines.append(f"{label} : {_fmt_num(record.get(key))}")
    lines.append(f"एकूण कर : {_fmt_num(record.get('totaltax'))}")
    return "\n".join(lines)
