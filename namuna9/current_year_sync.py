# नमुना-8 मध्ये मालमत्ता सेव्ह/बदल झाल्यावर (आणि "सर्व मालमत्तांचा कर पुन्हा मोजा" नंतर)
# गावाच्या फक्त सर्वात नवीन (चालू) नमुना-9 वर्षाचा आधीच जतन झालेला रो नमुना-8 शी जुळवतो.
#
# का: /namuna9/table-data एखादी मालमत्ता पहिल्यांदा दाखवताना त्या क्षणीचा कर
# namuna9_property_data मध्ये जतन करतो आणि नंतर नेहमी तोच जतन केलेला आकडा वापरतो. त्यामुळे
# नंतर नमुना-8 मध्ये बांधकाम/वर्ष/प्रकार/क्षेत्रफळ बदललं तरी नमुना-9 जुनाच (उदा. 0) राहायचा.
#
# नियम (फक्त चालू वर्षाचा रो, फक्त 6 चालू कर-प्रकार):
#   नवीन चालू = आत्ताची मागणी - त्या कर-प्रकारावर आधीच जमा झालेली चालू वसुली (vasuliChalu*)
#   एकूण/total पुन्हा मोजतो (collect / पावती एडिट सारखंच सूत्र).
#   वसुली > नवीन मागणी असेल तर चालू 0 (उणे नाही) आणि "जादा वसुली" म्हणून flag.
# कधीच बदलत नाही: जुनी वर्षं, पावत्या, वसुली रकमा, थकित (shakti*), दंड, नोटीस/वारंट फी.
# रो अजून नसेल तर काहीच करत नाही - table-data पहिल्यांदा उघडल्यावर ताज्या करावरूनच बनवतो.
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from namuna8.calculations.naumuna8_calculations import get_assessment_year
from namuna9 import namuna9_model
from namuna9.tax_calculations import calculate_total_house_tax
from location_management import models as location_models
from Utility.tax_rounding import get_tax_rounding_mode

# (कर-प्रकार, चालू फील्ड, चालू वसुली फील्ड, नाव)
HEADS = (
    ("Ghar", "chaluGhar", "vasuliChaluGhar", "घरपट्टी"),
    ("Diva", "chaluDiva", "vasuliChaluDiva", "दिवाबत्ती"),
    ("AarogyaKar", "chaluAarogyaKar", "vasuliChaluAarogyaKar", "आरोग्य कर"),
    ("Sapanikar", "chaluSapanikar", "vasuliChaluSapanikar", "सामान्य पाणी"),
    ("Vpanikar", "chaluVpanikar", "vasuliChaluVpanikar", "विशेष पाणी"),
    ("CleaningTax", "chaluCleaningTax", "vasuliChaluCleaningTax", "सफाई कर"),
)


def _yearslap_start_year(ys):
    try:
        return int(str(ys).split('-')[0])
    except Exception:
        return -1


def latest_year_record(db, village_id):
    """गावाचं सर्वात नवीन नमुना-9 वर्ष (table-data प्रमाणेच yearslap च्या सुरुवातीच्या वर्षावरून)."""
    records = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == str(village_id)
    ).all()
    if not records:
        return None
    return max(records, key=lambda r: _yearslap_start_year(r.yearslap))


def demand_context(db, gram_panchayat_id):
    """एकाच ग्रामपंचायतीच्या अनेक मालमत्तांसाठी सेटिंग्ज/कॅशे एकदाच (table-data सारखंच)."""
    gram_panchayat = db.query(location_models.GramPanchayat).filter_by(id=gram_panchayat_id).first()
    tax_settings = db.query(namuna8_model.Namuna8SettingTax).filter(
        namuna8_model.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    return {
        "gram_panchayat_id": gram_panchayat_id,
        "assessment_year": get_assessment_year(gram_panchayat),
        "general_setting": db.query(settingModels.GeneralSetting).filter_by().first(),
        "weightage_map": {row.building_usage: row.weightage for row in db.query(settingModels.BuildingUsageWeightage).all()},
        "tax_settings": tax_settings,
        "water_settings": db.query(namuna8_model.Namuna8WaterTaxSettings).filter(
            namuna8_model.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first(),
        "rounding_mode": get_tax_rounding_mode(db, gram_panchayat_id),
        "construction_type_cache": {},
        "depreciation_rate_cache": {},
    }


def current_demand(db, prop, ctx):
    """मालमत्तेची आत्ताची चालू मागणी - /namuna9/table-data नवीन रो बनवताना वापरतो तेच
    calculate_total_house_tax + build_property_response (घरपट्टी नमुना-8 च्या
    totalHouseTax शी जुळते)."""
    from namuna8.namuna8_apis import build_property_response
    gp_id = ctx["gram_panchayat_id"]
    prop_data = build_property_response(
        prop, db, gp_id, tax_settings=ctx["tax_settings"], water_settings=ctx["water_settings"],
        water_slab_settings=ctx["tax_settings"],
    )
    house_tax = calculate_total_house_tax(
        prop, prop.constructions, db, gram_panchayat_id=gp_id,
        general_setting=ctx["general_setting"], weightage_map=ctx["weightage_map"],
        construction_type_cache=ctx["construction_type_cache"], depreciation_rate_cache=ctx["depreciation_rate_cache"],
        rounding_mode=ctx["rounding_mode"], assessment_year=ctx["assessment_year"],
    )
    return {
        "Ghar": round(house_tax or 0, 2),
        "Diva": round(prop_data.get('divaKar', 0) or 0, 2),
        "AarogyaKar": round(prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0, 2),
        "Sapanikar": round(prop_data.get('sapanikar', 0) or 0, 2),
        "Vpanikar": round(prop_data.get('vpanikar', 0) or 0, 2),
        "CleaningTax": round(prop_data.get('cleaningTax', 0) or 0, 2),
    }


def _ekun_total(row, chalu):
    """एकूण व total - _adjust_property_data_for_receipt / bulk-update सारखंच सूत्र."""
    ekun = {
        "Ghar": (row.shaktiGhar or 0) + chalu["Ghar"] + (row.dand or 0),
        "Diva": (row.shaktiDiva or 0) + chalu["Diva"],
        "AarogyaKar": (row.shaktiAarogyaKar or 0) + chalu["AarogyaKar"],
        "Sapanikar": (row.shaktiSapanikar or 0) + chalu["Sapanikar"],
        "Vpanikar": (row.shaktiVpanikar or 0) + chalu["Vpanikar"],
        "CleaningTax": (row.shaktiCleaningTax or 0) + chalu["CleaningTax"],
    }
    ekun = {k: round(v, 2) for k, v in ekun.items()}
    total = round(sum(ekun.values()) + (row.noticeFee or 0) + (row.warrantFee or 0) + (row.dand or 0), 2)
    return ekun, total


def plan_row(row, demand):
    """DB ला हात न लावता: रो साठी नवीन चालू/एकूण/total आणि जादा वसुली."""
    heads = {}
    new_chalu = {}
    overpaid = []
    changed = False
    for key, chalu_field, vasuli_field, label in HEADS:
        old = round(getattr(row, chalu_field) or 0, 2)
        paid = round(getattr(row, vasuli_field) or 0, 2)
        new = round(demand[key] - paid, 2)
        extra = 0.0
        if new < 0:
            extra, new = round(-new, 2), 0.0
            overpaid.append({"head": label, "demand": demand[key], "paid": paid, "extra": extra})
        new_chalu[key] = new
        heads[key] = {"old": old, "demand": demand[key], "paid": paid, "new": new, "overpaid": extra}
        if old != new:
            changed = True
    ekun, total = _ekun_total(row, new_chalu)
    return {
        "heads": heads,
        "new_chalu": new_chalu,
        "ekun": ekun,
        "old_total": round(row.total or 0, 2),
        "new_total": total,
        "overpaid": overpaid,
        "changed": changed or round(row.total or 0, 2) != total,
    }


def apply_plan(row, plan):
    for key, chalu_field, _vasuli_field, _label in HEADS:
        setattr(row, chalu_field, plan["new_chalu"][key])
        setattr(row, "ekun" + key, plan["ekun"][key])
    row.total = plan["new_total"]


def sync_property(db, prop, ctx=None, commit=True):
    """एका मालमत्तेचा चालू नमुना-9 रो अद्ययावत करतो (commit=False: कॉलरच्या चालू
    transaction मध्येच, उदा. POST चं `with db.begin()`). परत: None (चालू वर्ष/रो नाही)
    किंवा {"yearslap", "updated", "overpaid"} - PUT/POST च्या response मध्ये जातो."""
    rec = latest_year_record(db, prop.village_id)
    if rec is None:
        return None
    row = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == rec.id,
        namuna9_model.Namuna9PropertyData.property_id == prop.id,
    ).first()
    if row is None:
        return None
    if ctx is None:
        ctx = demand_context(db, prop.gram_panchayat_id)
    plan = plan_row(row, current_demand(db, prop, ctx))
    if plan["changed"]:
        apply_plan(row, plan)
        if commit:
            db.commit()
        else:
            db.flush()
    return {"yearslap": rec.yearslap, "updated": plan["changed"], "overpaid": plan["overpaid"]}


def plan_properties(db, properties, ctx):
    """"कर पुन्हा मोजा" साठी: [(prop, rec, row, plan)] - फक्त ज्यांचा चालू वर्षाचा रो आहे.
    DB बदलत नाही. calculate_total_house_tax बांधकाम रो वरचा जतन केलेला houseTax वापरत
    नाही (स्वतः मोजतो), म्हणून बांधकाम रो अद्ययावत होण्याआधीही हाच निकाल येतो."""
    latest_by_village = {}
    for village_id in {p.village_id for p in properties}:
        latest_by_village[village_id] = latest_year_record(db, village_id)
    rec_ids = [r.id for r in latest_by_village.values() if r is not None]
    rows = {}
    if rec_ids:
        for row in db.query(namuna9_model.Namuna9PropertyData).filter(
                namuna9_model.Namuna9PropertyData.namuna9_id.in_(rec_ids)).all():
            rows[(row.namuna9_id, row.property_id)] = row
    out = []
    for prop in properties:
        rec = latest_by_village.get(prop.village_id)
        row = rows.get((rec.id, prop.id)) if rec is not None else None
        if row is None:
            continue
        out.append((prop, rec, row, plan_row(row, current_demand(db, prop, ctx))))
    return out
