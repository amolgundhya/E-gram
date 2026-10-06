"""मालमत्तेच्या सर्व QR कोड्ससाठी (नमुना-8 प्रिंट QR, नमुना-9/house QR, कचरा
sticker QR, नाव प्लेट QR) समान, वाचनीय plain-text मजकूर तयार करतो - JSON ऐवजी,
जेणेकरून कोणत्याही सामान्य QR स्कॅनर अ‍ॅपने स्कॅन केल्यावर माणसाला थेट वाचता यावं.

सर्व 4 ठिकाणी हाच एक function वापरायचा, जेणेकरून मजकुराचं स्वरूप कायम सुसंगत राहील.
"""


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
        total_area_fmt = f"%.{decimals}f" % float(total_area)
        if avg_length and avg_width:
            lines.append(f"एकूण क्षेत्रफळ : {_fmt_num(avg_length)} X {_fmt_num(avg_width)} = {total_area_fmt} {unit_lbl}")
        else:
            lines.append(f"एकूण क्षेत्रफळ : {total_area_fmt} {unit_lbl}")

    for c in (record.get("constructionType") or []):
        c_type_raw = (c.get("type") or "").strip()
        length = c.get("length") or 0
        width = c.get("width") or 0
        area = round(length * width, 2)
        if not c_type_raw or c_type_raw.startswith("खाली जागा"):
            # खाली-जागा-प्रकारची construction रो "बांधकाम" म्हणून दाखवायची नाही - ती
            # जागा get_property_record मध्येच खाली जागाच्या एकूण बेरजेत आधी धरलेली
            # असते (खाली khaliJaga[0] मधून तेच वाचतो), इथे परत बेरीज करायची नाही
            # (दोनदा मोजली जाईल).
            continue
        if not area:
            continue
        area_fmt = f"%.{decimals}f" % area
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
            khali_fmt = f"%.{decimals}f" % float(khali_area)
            lines.append(f"खाली जागा : {khali_fmt} {unit_lbl}")

    return lines


def build_property_qr_text(record: dict, parent_gp_name: str = None, year_label: str = None) -> str:
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
    वापरत नाही, पण इतर कॉलर्सशी सुसंगत राहण्यासाठी parameter तसाच ठेवलाय)."""
    lines = [
        f"अ.क्र. : {record.get('srNo') or ''}",
        f"मालमत्ता क्र. : {record.get('propertyNumber') or ''}",
        f"मालक : {record.get('ownerName') or ''}",
        f"भोगवट : {record.get('occupantName') or 'स्वतः'}",
    ]
    lines.extend(build_area_lines(record, include_type=False))
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
    for label, amount in tax_items:
        if _fmt_num(amount) != "0":
            lines.append(f"{label} : {_fmt_num(amount)}")
    lines.append(f"एकूण कर : {_fmt_num(record.get('totaltax'))}")

    return "\n".join(lines)
