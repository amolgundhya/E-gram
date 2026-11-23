from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate, get_assessment_year
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from location_management import models as location_models
from Utility.tax_rounding import round_tax_amount, get_tax_rounding_mode, round_half_up
from datetime import datetime
from namuna8.calculations.khali_jaga import property_house_tax, has_vacant_land
import math
from decimal import Decimal, ROUND_HALF_UP

def calculate_total_house_tax(
    prop, constructions, db, gram_panchayat_id=None,
    general_setting=None, weightage_map=None,
    construction_type_cache=None, depreciation_rate_cache=None,
    rounding_mode=None, assessment_year=None,
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
    if assessment_year is None:
        # घसारा दर आकारणी चक्राच्या सुरुवातीच्या वर्षावरून (from_yearslap) काढायचा,
        # आजच्या तारखेवरून नाही - कॉलरने आधीच दिलेलं नसेल तरच इथे एकदा काढतो.
        gp_for_year = db.query(location_models.GramPanchayat).filter_by(id=gp_id).first() if gp_id else None
        assessment_year = get_assessment_year(gp_for_year)

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
            depreciation_rate_cache[key] = calculate_depreciation_rate(year, name, assessment_year)
        return depreciation_rate_cache[key]

    def _round_tax(value):
        # rounding_mode पास केला नसेल (जुने कॉलर्स) तर आधीसारखंच round_tax_amount
        # (स्वतःची क्वेरी करणारं) वापरतो; पास केला असेल तर तीच मोड वापरून इथेच ठरवतो.
        if rounding_mode is None:
            return round_tax_amount(value, db, gp_id)
        # "Round Up All Area" ON/OFF दोन्हीत साधारण राउंडिंग (23-Nov-2026, आधी ON = ceil).
        return round_half_up(value)

    # नमुना-8 प्रमाणेच: प्रत्येक बांधकाम रो चा जतन केलेला houseTax (नोंद/PUT/"सर्व कर पुन्हा
    # मोजा" ने compute_construction_values मधून साठवलेला) + खाली जागा (फक्त तळमजला वजा).
    # आधी इथे प्रत्येक बांधकामाचा कर पुन्हा live मोजला जायचा आणि खाली जागेतून सर्व मजले वजा
    # व्हायचे - त्यामुळे नमुना-8 व नमुना-9 घरपट्टी वेगळी यायची (क्लायंट Nov-2026).
    khali_type = _construction_type_by_name(getattr(prop, 'vacantLandType', None)) if has_vacant_land(prop) else None
    return _round_tax(property_house_tax(prop, constructions, khali_type, _round_tax))

