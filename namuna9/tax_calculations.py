from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from Utility.tax_rounding import round_tax_amount, get_tax_rounding_mode
from datetime import datetime
import math
from decimal import Decimal, ROUND_HALF_UP

def calculate_total_house_tax(
    prop, constructions, db, gram_panchayat_id=None,
    general_setting=None, weightage_map=None,
    construction_type_cache=None, depreciation_rate_cache=None,
    rounding_mode=None,
):
    # general_setting/weightage_map/construction_type_cache/depreciation_rate_cache/
    # rounding_mode: पास केले नसतील (जुन्या सगळ्या कॉलर्ससाठी डिफॉल्ट None) तर आधीसारखेच
    # इथे क्वेरी करतो. जिथे हे शेकडो मालमत्तांसाठी लूपमध्ये वारंवार बोलावलं जातं (नमुना-9
    # माहिती दाखवा), तिथे कॉलर एकदाच fetch करून/रिकामी कॅशे बनवून हे पास करू शकतो आणि तीच
    # कॅशे सगळ्या मालमत्तांसाठी पुन्हा वापरू शकतो - निकाल आधीसारखाच, फक्त पुन्हा क्वेरी होत नाही.
    karLaguNahi = bool(getattr(prop, 'karLaguNahi', False))
    if karLaguNahi:
        return 0.0

    gp_id = gram_panchayat_id or getattr(prop, 'gram_panchayat_id', None)
    if general_setting is None:
        general_setting = db.query(settingModels.GeneralSetting).filter_by().first()
    formula1 = general_setting.capitalFormula1 if general_setting else None
    if weightage_map is None:
        weightage_map = {row.building_usage: row.weightage for row in db.query(settingModels.BuildingUsageWeightage).all()}
    if construction_type_cache is None:
        construction_type_cache = {}
    if depreciation_rate_cache is None:
        depreciation_rate_cache = {}

    def _construction_type_by_id(ctype_id):
        key = ('id', ctype_id)
        if key not in construction_type_cache:
            construction_type_cache[key] = db.query(namuna8_model.ConstructionType).filter_by(id=ctype_id).first()
        return construction_type_cache[key]

    def _construction_type_by_name(name):
        key = ('name', name)
        if key not in construction_type_cache:
            construction_type_cache[key] = db.query(namuna8_model.ConstructionType).filter(namuna8_model.ConstructionType.name == name).first()
        return construction_type_cache[key]

    def _cached_depreciation_rate(year, name):
        key = (year, name)
        if key not in depreciation_rate_cache:
            depreciation_rate_cache[key] = calculate_depreciation_rate(year, name)
        return depreciation_rate_cache[key]

    def _round_tax(value):
        # rounding_mode पास केला नसेल (जुने कॉलर्स) तर आधीसारखंच round_tax_amount
        # (स्वतःची क्वेरी करणारं) वापरतो; पास केला असेल तर तीच मोड वापरून इथेच ठरवतो.
        if rounding_mode is None:
            return round_tax_amount(value, db, gp_id)
        if rounding_mode == "ceil":
            return math.ceil(value)
        return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    totalHouseTax = 0
    unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
    # बांधकाम लांबी/रुंदी प्रॉपर्टीच्या स्वतःच्या constructionAreaUnit मध्ये असू शकतात, जे
    # areaUnit (प्लॉटचं एकक) पेक्षा वेगळं असू शकतं - चौ.फुट आकडा चुकून चौ.मी. समजून गणना
    # झाल्यास क्षेत्रफळ ~10.76 पट जास्त धरलं जातं. टाईप केलेल्या एककातच क्षेत्रफळ काढून,
    # गरज असेल तरच शेअर्ड 10.76 फॅक्टरने एकदाच मीटरमध्ये रूपांतर करतो.
    construction_unit = getattr(prop, 'constructionAreaUnit', None) or unit
    for c in constructions:
        construction_type = _construction_type_by_id(c.construction_type_id)
        if not construction_type:
            continue
        raw_area = (c.length or 0) * (c.width or 0)
        area_m = raw_area if construction_unit == 'sqm' else round(raw_area / 10.76, 4)
        depreciation_rate = _cached_depreciation_rate(c.constructionYear, construction_type.name)
        usage_factor = weightage_map.get(getattr(c, 'bharank', None), 1)
        annual_land_value_rate = getattr(construction_type, 'annualLandValueRate', 1)
        bandhmastache_dar = getattr(construction_type, 'bandhmastache_dar', 0)
        if formula1:
            capital_value = ((area_m * annual_land_value_rate) + (area_m * bandhmastache_dar * (depreciation_rate/100))) * usage_factor
        else:
            capital_value = area_m * annual_land_value_rate * depreciation_rate/100 * usage_factor
        # भांडवली मूल्य राउंड करत नाही - फक्त 2 दशांश स्थळांपर्यंत ठेवतो; फक्त कर रक्कम राउंड होते.
        capital_value = round(capital_value, 2)
        house_tax = _round_tax((getattr(construction_type, 'rate', 0) / 1000) * capital_value)
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
            khali_construction_type = _construction_type_by_name(vacant_land_type)
            if khali_construction_type:
                annual_land_value_rate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                capital_value_kj = round(area_in_meter * annual_land_value_rate, 2)
                totalHouseTax += _round_tax((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value_kj)
    return _round_tax(totalHouseTax)

