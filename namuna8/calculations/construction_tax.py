# एका बांधकाम रो चं भांडवली मूल्य व घरपट्टी - नमुना-8 नोंद (POST), संपादन (PUT) आणि
# "सर्व मालमत्तांचा कर पुन्हा मोजा" (admin/recalculate_taxes) तिघंही हेच एक फंक्शन
# वापरतात, म्हणजे पुन्हा मोजलेला कर हा मालमत्ता उघडून पुन्हा सेव्ह केल्यावर येणाऱ्या
# करासारखाच अगदी तंतोतंत (तेच क्षेत्रफळ रूपांतर, तोच घसारा, तोच राउंडिंग नियम) राहतो.
from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
from Utility.tax_rounding import round_tax_amount

# चौ.फु. -> चौ.मी. (नमुना-8 सेव्हमध्ये आधीपासून वापरलेलाच आकडा)
SQFT_TO_SQM = 0.092937


def compute_construction_values(db, construction_type, length, width, construction_year, bharank,
                                construction_unit, assessment_year, formula1, weightage_map,
                                gram_panchayat_id):
    """(capital_value, house_tax) परत करतो. construction_unit: बांधकाम लांबी/रुंदीचं
    एकक (property.constructionAreaUnit, नसेल तर areaUnit) - 'sqm' असेल तर थेट मीटर,
    नाहीतर चौ.फु. धरून SQFT_TO_SQM ने रूपांतर. formula1: GeneralSetting.capitalFormula1
    (जमीन + इमारत); नसेल तर formula2 (फक्त जमीन x घसारा). भांडवली मूल्य 2 दशांश
    स्थळांपर्यंत, घरपट्टी round_tax_amount ने पूर्ण रुपयात."""
    annual_land_value_rate = getattr(construction_type, 'annualLandValueRate', 1)
    if construction_unit == 'sqm':
        area_in_meter = (length or 0) * (width or 0)
    else:
        area_in_meter = (length or 0) * (width or 0) * SQFT_TO_SQM
    construction_rate = construction_type.bandhmastache_dar
    depreciation_rate = calculate_depreciation_rate(construction_year, construction_type.name, assessment_year)
    usage_factor = weightage_map.get(bharank, 1)
    if formula1:
        capital_value = ((area_in_meter * annual_land_value_rate) + (area_in_meter * construction_rate * (depreciation_rate / 100))) * usage_factor
    else:
        capital_value = area_in_meter * annual_land_value_rate * depreciation_rate / 100 * usage_factor
    capital_value = round(capital_value, 2)
    house_tax = round_tax_amount((getattr(construction_type, 'rate', 0) / 1000) * capital_value, db, gram_panchayat_id)
    return capital_value, house_tax
