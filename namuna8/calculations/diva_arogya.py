"""दिवा (वीज) / आरोग्य कर लागू होतो का - नमुना-8 (नोंद, प्रिंट, यादी, Bulk) आणि नमुना-9
(मागणी, current_year_sync, सर्व कर पुन्हा मोजा) सगळे हेच एक फंक्शन वापरतात.

नियम:
- "कर लागू नाही" किंवा मालमत्तेवर "दिवा / आरोग्य कर काढा" -> लागू नाही (पूर्वीसारखेच).
- Master "खाली जागेवर दिवा, आरोग्य" (Namuna8DropdownAddSettings.khalijagevarAarogya):
  मालमत्तेवर एकही खरे बांधकाम नसेल (सगळी जागा खाली जागा - उदा. सर्व बांधकाम रो काढल्या)
  तर दिवा/आरोग्य फक्त ही सेटिंग "होय" असेल तरच. सेटिंग कधीच जतन केली नसेल (None) तर
  "होय" - म्हणजे आजपर्यंतचंच वर्तन. बांधकाम असलेल्या मालमत्तांना ही सेटिंग लागू नाही.
"""
from namuna8 import namuna8_model as models


def khali_jaga_diva_arogya_allowed(db, gram_panchayat_id) -> bool:
    """Master "खाली जागेवर दिवा, आरोग्य" - None/नसेल तर True (होय)."""
    if not gram_panchayat_id:
        return True
    row = db.query(models.Namuna8DropdownAddSettings.khalijagevarAarogya).filter(
        models.Namuna8DropdownAddSettings.gram_panchayat_id == gram_panchayat_id
    ).first()
    if row is None or row[0] is None:
        return True
    return bool(row[0])


def has_real_construction(constructions) -> bool:
    """"खाली जागा" प्रकाराशिवायची, क्षेत्रफळ > 0 असलेली एक तरी बांधकाम रो."""
    for c in constructions or []:
        ct = getattr(c, "construction_type", None)
        name = (getattr(ct, "name", None) or "").strip()
        if name.startswith("खाली जागा"):
            continue
        if (getattr(c, "length", None) or 0) * (getattr(c, "width", None) or 0) > 0:
            return True
    return False


def diva_arogya_applies(prop, khali_allowed: bool, constructions=None) -> bool:
    if getattr(prop, "karLaguNahi", False) or getattr(prop, "divaArogyaKar", False):
        return False
    if khali_allowed:
        return True
    rows = constructions if constructions is not None else getattr(prop, "constructions", None)
    return has_real_construction(rows)
