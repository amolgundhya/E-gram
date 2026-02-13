import math
from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from datetime import datetime

def calculate_total_house_tax(prop, constructions, db):
    karLaguNahi = bool(getattr(prop, 'karLaguNahi', False))
    if karLaguNahi:
        return 0.0

    userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
    formula1 = userFormulaPreference.capitalFormula1 if userFormulaPreference else None
    weightage_map = {row.building_usage: row.weightage for row in db.query(settingModels.BuildingUsageWeightage).all()}

    totalHouseTax = 0
    unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
    for c in constructions:
        construction_type = db.query(namuna8_model.ConstructionType).filter_by(id=c.construction_type_id).first()
        if not construction_type:
            continue
        if unit == 'sqm':
            area_m = (c.length or 0) * (c.width or 0)
        else:
            area_m = (c.length or 0) * (c.width or 0) * 0.092903
        depreciation_rate = calculate_depreciation_rate(c.constructionYear, construction_type.name)
        usage_factor = weightage_map.get(getattr(c, 'bharank', None), 1)
        annual_land_value_rate = getattr(construction_type, 'annualLandValueRate', 1)
        bandhmastache_dar = getattr(construction_type, 'bandhmastache_dar', 0)
        if formula1:
            capital_value = ((area_m * annual_land_value_rate) + (area_m * bandhmastache_dar * (depreciation_rate/100))) * usage_factor
        else:
            capital_value = area_m * annual_land_value_rate * depreciation_rate/100 * usage_factor
        capital_value = math.ceil(capital_value)
        house_tax = math.ceil((getattr(construction_type, 'rate', 0) / 1000) * capital_value)
        totalHouseTax += house_tax
    # Add khali jaga if needed, using the same logic
    vacant_land_type = getattr(prop, 'vacantLandType', None)
    if vacant_land_type not in [None, '', 'null']:
        if unit == 'sqm':
            total_area = prop.totalArea or 0
            used_area = round(sum((c.length or 0) * (c.width or 0) for c in constructions), 2)
            khali_area = round(max(total_area - used_area, 0), 2)
            area_in_meter = khali_area
        else:
            total_area = prop.totalAreaSqFt or 0
            used_area = round(sum((c.length or 0) * (c.width or 0) for c in constructions), 2)
            khali_area = round(max(total_area - used_area, 0), 2)
            area_in_meter = round(khali_area * 0.092903, 2)
        if khali_area > 0:
            khali_construction_type = db.query(namuna8_model.ConstructionType).filter(namuna8_model.ConstructionType.name == vacant_land_type).first()
            if khali_construction_type:
                annual_land_value_rate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                if formula1:
                    capital_value_kj = math.ceil(area_in_meter * annual_land_value_rate)
                else:
                    capital_value_kj = math.ceil(area_in_meter * annual_land_value_rate)
                totalHouseTax += math.ceil((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value_kj)
    return math.ceil(totalHouseTax)

