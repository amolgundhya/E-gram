# एका बांधकाम रो चं भांडवली मूल्य व घरपट्टी - नमुना-8 नोंद (POST), संपादन (PUT) आणि
# "सर्व मालमत्तांचा कर पुन्हा मोजा" (admin/recalculate_taxes) तिघंही हेच एक फंक्शन
# वापरतात, म्हणजे पुन्हा मोजलेला कर हा मालमत्ता उघडून पुन्हा सेव्ह केल्यावर येणाऱ्या
# करासारखाच अगदी तंतोतंत (तेच क्षेत्रफळ रूपांतर, तोच घसारा, तोच राउंडिंग नियम) राहतो.
from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
from Utility.tax_rounding import round_tax_amount

# चौ.फु. -> चौ.मी. रूपांतर व राउंडिंग Utility.area_units मधून (÷10.764, 2 दशांश) - नमुना-8,
# खाली जागा व नमुना-9 सगळीकडे तोच.
from Utility.area_units import area_sqm_for_tax
# भारांक: नेमकं नाव -> जुनं नाव ("वाणिज्य" -> "वाणिज्यिक") -> 1 (Utility/usage_weight.py)
from Utility.usage_weight import usage_weight


def compute_construction_values(db, construction_type, length, width, construction_year, bharank,
                                construction_unit, assessment_year, formula1, weightage_map,
                                gram_panchayat_id):
    """(capital_value, house_tax) परत करतो. construction_unit: बांधकाम लांबी/रुंदीचं
    एकक (property.constructionAreaUnit, नसेल तर areaUnit) - 'sqm' असेल तर थेट मीटर,
    नाहीतर चौ.फु. धरून area_sqm_for_tax ने रूपांतर (दोन्हीत चौ.मी. 2 दशांश). formula1: GeneralSetting.capitalFormula1
    (जमीन + इमारत); नसेल तर formula2 (फक्त जमीन x घसारा). भांडवली मूल्य 2 दशांश
    स्थळांपर्यंत, घरपट्टी round_tax_amount ने पूर्ण रुपयात."""
    annual_land_value_rate = getattr(construction_type, 'annualLandValueRate', 1)
    area_in_meter = area_sqm_for_tax((length or 0) * (width or 0), 'sqm' if construction_unit == 'sqm' else 'sqft')
    construction_rate = construction_type.bandhmastache_dar
    depreciation_rate = calculate_depreciation_rate(construction_year, construction_type.name, assessment_year)
    usage_factor = usage_weight(weightage_map, bharank)
    if formula1:
        capital_value = ((area_in_meter * annual_land_value_rate) + (area_in_meter * construction_rate * (depreciation_rate / 100))) * usage_factor
    else:
        capital_value = area_in_meter * annual_land_value_rate * depreciation_rate / 100 * usage_factor
    capital_value = round(capital_value, 2)
    house_tax = round_tax_amount((getattr(construction_type, 'rate', 0) / 1000) * capital_value, db, gram_panchayat_id)
    return capital_value, house_tax
