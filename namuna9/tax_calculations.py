from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from Utility.tax_rounding import round_tax_amount
from datetime import datetime

def calculate_total_house_tax(prop, constructions, db, gram_panchayat_id=None):
    karLaguNahi = bool(getattr(prop, 'karLaguNahi', False))
    if karLaguNahi:
        return 0.0

    gp_id = gram_panchayat_id or getattr(prop, 'gram_panchayat_id', None)
    userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
    formula1 = userFormulaPreference.capitalFormula1 if userFormulaPreference else None
    weightage_map = {row.building_usage: row.weightage for row in db.query(settingModels.BuildingUsageWeightage).all()}

    totalHouseTax = 0
    unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
    # बांधकाम लांबी/रुंदी प्रॉपर्टीच्या स्वतःच्या constructionAreaUnit मध्ये असू शकतात, जे
    # areaUnit (प्लॉटचं एकक) पेक्षा वेगळं असू शकतं - चौ.फुट आकडा चुकून चौ.मी. समजून गणना
    # झाल्यास क्षेत्रफळ ~10.76 पट जास्त धरलं जातं. टाईप केलेल्या एककातच क्षेत्रफळ काढून,
    # गरज असेल तरच शेअर्ड 10.76 फॅक्टरने एकदाच मीटरमध्ये रूपांतर करतो.
    construction_unit = getattr(prop, 'constructionAreaUnit', None) or unit
    for c in constructions:
        construction_type = db.query(namuna8_model.ConstructionType).filter_by(id=c.construction_type_id).first()
        if not construction_type:
            continue
        raw_area = (c.length or 0) * (c.width or 0)
        area_m = raw_area if construction_unit == 'sqm' else round(raw_area / 10.76, 4)
        depreciation_rate = calculate_depreciation_rate(c.constructionYear, construction_type.name)
        usage_factor = weightage_map.get(getattr(c, 'bharank', None), 1)
        annual_land_value_rate = getattr(construction_type, 'annualLandValueRate', 1)
        bandhmastache_dar = getattr(construction_type, 'bandhmastache_dar', 0)
        if formula1:
            capital_value = ((area_m * annual_land_value_rate) + (area_m * bandhmastache_dar * (depreciation_rate/100))) * usage_factor
        else:
            capital_value = area_m * annual_land_value_rate * depreciation_rate/100 * usage_factor
        capital_value = round_tax_amount(capital_value, db, gp_id)
        house_tax = round_tax_amount((getattr(construction_type, 'rate', 0) / 1000) * capital_value, db, gp_id)
        totalHouseTax += house_tax
    # Add khali jaga if needed, using the same logic. खाली जागा नेहमी प्लॉटच्याच
    # एककात (unit) मोजतो - बांधकामाचा वापरलेला भाग वजा करण्याआधी गरज असल्यास तेवढंच
    # एकदा रूपांतरित करतो (property_record_response.py च्या खाली जागा गणनेप्रमाणेच).
    vacant_land_type = getattr(prop, 'vacantLandType', None)
    if vacant_land_type not in [None, '', 'null']:
        total_area = (prop.totalArea or 0) if unit == 'sqm' else (prop.totalAreaSqFt or 0)
        construction_sum = round(sum((c.length or 0) * (c.width or 0) for c in constructions), 2)
        if construction_unit == unit:
            used_area = construction_sum
        else:
            used_area = round(construction_sum * 10.76, 2) if unit == 'sqft' else round(construction_sum / 10.76, 2)
        khali_area = round(max(total_area - used_area, 0), 2)
        area_in_meter = khali_area if unit == 'sqm' else round(khali_area / 10.76, 2)
        if khali_area > 0:
            khali_construction_type = db.query(namuna8_model.ConstructionType).filter(namuna8_model.ConstructionType.name == vacant_land_type).first()
            if khali_construction_type:
                annual_land_value_rate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                capital_value_kj = round_tax_amount(area_in_meter * annual_land_value_rate, db, gp_id)
                totalHouseTax += round_tax_amount((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value_kj, db, gp_id)
    return round_tax_amount(totalHouseTax, db, gp_id)

