from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from namuna8 import namuna8_model as models
from namuna8 import namuna8_schemas as schemas
from database import get_db
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
import os
from namuna8.mastertab.mastertabmodels import BuildingUsageWeightage
from namuna8.mastertab import mastertabmodels as settingModels
from location_management import models as location_models
from datetime import datetime,date

backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

router = APIRouter()

# Helper to calculate house tax
def calc_house_tax(rate):
    try:
        if rate is None:
            return 0
        capital_value = 541133
        return round((float(rate) / 1000) * capital_value)
    except Exception:
        return 0

# Deep rounding for all numeric fields (excluding booleans) using HALF_UP,
# but preserve decimals for specific keys like 'length' and 'width'.
EXEMPT_FLOAT_KEYS = {"length", "width"}

def _deep_round_numbers(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                if k in EXEMPT_FLOAT_KEYS:
                    # keep as float; do not coerce to int
                    continue
                try:
                    obj[k] = int(Decimal(v).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
                except Exception:
                    obj[k] = int(v)
            elif isinstance(v, (dict, list)):
                _deep_round_numbers(v)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            v = obj[i]
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                # list elements don't have keys; assume not exempt
                try:
                    obj[i] = int(Decimal(v).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
                except Exception:
                    obj[i] = int(v)
            elif isinstance(v, (dict, list)):
                _deep_round_numbers(v)

@router.get("/property_record/{anuKramank}")
def get_property_record(
    anuKramank: int, 
    village_id:int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    prop = (
        db.query(models.Property)
        .filter(
            models.Property.anuKramank == anuKramank,
            models.Property.village_id == village_id
        )
        .first()
     )

    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Validate that the property's location fields match the specified parameters
    if prop.district_id != district_id:
        raise HTTPException(status_code=400, detail="Property does not belong to the specified district")
    
    if prop.taluka_id != taluka_id:
        raise HTTPException(status_code=400, detail="Property does not belong to the specified taluka")
    
    if prop.gram_panchayat_id != gram_panchayat_id:
        raise HTTPException(status_code=400, detail="Property does not belong to the specified gram panchayat")
    owner_ids = [o.id for o in prop.owners]
    property_types = [c.construction_type.name for c in prop.constructions]
    property_description = ", ".join(property_types)
    # khaliJaga logic
    khaliJaga = []
    if getattr(prop, 'vacantLandType', None) not in [None, '', 'null']:
        # Compute khali area in both sqm and sqft based on stored unit
        unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
        if unit == 'sqm':
            total_area_m = round(prop.totalArea or 0, 2)
            used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in prop.constructions), 2)
        else:
            total_area_m = round((prop.totalAreaSqFt or 0) * 0.092903, 2)
            used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in prop.constructions) * 0.092903, 2)
        khali_area_m = round(max(total_area_m - used_area_m, 0), 2)
        khali_area = round(khali_area_m / 0.092903, 2)
        # Find the bandhmastache_dar for vacantLandType construction type
        khali_jaga_rate = 0
        vacant_construction_type = None
       
        if prop.vacantLandType:
            # Query database directly for the construction type, regardless of property constructions
            vacant_construction_type = db.query(models.ConstructionType).filter(models.ConstructionType.name == prop.vacantLandType).first()
            if vacant_construction_type:
                khali_jaga_rate = getattr(vacant_construction_type, 'bandhmastache_dar', 0)
            else:
                # Fallback: try to find any construction type with similar name
                similar_construction = db.query(models.ConstructionType).filter(models.ConstructionType.name.like(f"%{prop.vacantLandType}%")).first()
                if similar_construction:
                    khali_jaga_rate = getattr(similar_construction, 'bandhmastache_dar', 0)
        # Calculate capital value and house tax for khali jaga using same logic as Namuna8
        if khali_area > 0:
            # Get construction type for khali jaga
            khali_construction_type = db.query(models.ConstructionType).filter(models.ConstructionType.name == "खाली जागा").first()
            
            if khali_construction_type:
                # Get user formula preference - same as Namuna8
                userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
                
                if userFormulaPreference:
                    formula1 = userFormulaPreference.capitalFormula1
                    formula2 = userFormulaPreference.capitalFormula2
                else:
                    formula1 = None
                    formula2 = None
                
                # Calculate area in meters - same as Namuna8
                AreaInMeter = round(khali_area * 1 * 0.092903, 2)  # length * width * 0.092903
                AnnualLandValueRate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                ConstructionRateAsPerConstruction = khali_construction_type.bandhmastache_dar
                depreciationRate = calculate_depreciation_rate(datetime.now().year, khali_construction_type.name)
                
                # Get usage weightage factor - same as Namuna8
                weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
                usageBasedBuildingWeightageFactor = weightage_map.get(prop.vacantLandType, 1)
                
                # Calculate capital value - exact same logic as Namuna8
                if formula1:
                    capital_value = (khali_area_m * AnnualLandValueRate)
                else:
                    capital_value = AreaInMeter * AnnualLandValueRate
                capital_value = round(capital_value, 2)
                
                # Calculate house tax - exact same logic as Namuna8
                house_tax = round((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value)
            else:
                capital_value = 0
                house_tax = 0
            
                
            khaliJaga = [{
                "constructiontype": prop.vacantLandType,
                "length": round(khali_area, 2),
                "width": 1,
                "year": datetime.now().year,
                "rate": khali_jaga_rate,
                "floor": "तळमजला",
                "usage": prop.vacantLandType,
                "capitalValue": 0 if prop.karLaguNahi else round(capital_value, 2),
                "houseTax": 0 if prop.karLaguNahi else house_tax,
                "usageBasedBuildingWeightageFactor": weightage_map.get(getattr(khali_construction_type, 'bharank', None), 1),
                "taxRates": 0 if prop.karLaguNahi else (getattr(khali_construction_type, 'rate', 0) if khali_area > 0 else 0),
                "totalkhalijagaareainfoot": round(khali_area, 2),
                "totalkhalijagaareainmeters": round(khali_area * 0.092903, 2)
            }]
    # else: khaliJaga remains []
    # Fetch weightage mapping for usage
    weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
    constructionType = [
        {
            "type": c.construction_type.name,
            "length": c.length,
            "width": c.width,
            "year": c.constructionYear,
            "rate": getattr(c.construction_type, 'bandhmastache_dar', 0),
            "floor": c.floor,
            "usage": getattr(c, 'bharank', None),
            "capitalValue": c.capitalValue,
            "houseTax": c.houseTax,
            "depreciation_rate": calculate_depreciation_rate(c.constructionYear, c.construction_type.name),
            "usageBasedBuildingWeightageFactor": weightage_map.get(getattr(c, 'bharank', None), 1),
            "taxRates": getattr(c.construction_type, 'rate', 0),
        }
        for c in prop.constructions
    ]
    # If tax not applicable, zero out construction financials
    if prop.karLaguNahi:
        for item in constructionType:
            item["capitalValue"] = 0
            item["houseTax"] = 0
            item["taxRates"] = 0
    owner = prop.owners[0] if prop.owners else None
    # Find the first owner with a non-null ownerPhoto
    photo_url = None
    for o in prop.owners:
        if getattr(o, 'ownerPhoto', None):
            photo_url = f"{backend_url}/{o.ownerPhoto.replace(os.sep, '/')}"
            break
    # Fetch Namuna8SettingTax row
    settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    water_settings = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
    water_slab_settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    def get_tax_by_area(area, field):
        if not settings:
            return 0
        if area is None:
            area = 0
        if area <= 300:
            return getattr(settings, field + 'Upto300', 0) or 0
        elif 301 <= area <= 700:
            return getattr(settings, field + '301_700', 0) or 0
        else:
            return getattr(settings, field + 'Above700', 0) or 0
    def get_water_facility_price(facility):
        if not facility:
            return 0
        if not water_settings or not water_slab_settings:
            return 0
        # Accept both spellings for 'सामान्य पाणीकर' and 'सामान्य पाणीकर'
        if facility in ['सामान्य पाणीकर', 'सामान्य पाणीकर']:
            return getattr(water_settings, 'generalWater', 0)
        elif facility == 'घरगुती नळ':
            return getattr(water_settings, 'houseTax', 0)
        elif facility == 'व्यावसायिक नळ':
            return getattr(water_settings, 'commercialTax', 0)
        elif facility == 'करास पात्र नसलेली इमारत':
            return getattr(water_settings, 'exemptRate', 0)
        elif facility == 'सामान्य पाणीकर १ ते ३०० चौ. फु.':
            return getattr(water_slab_settings, 'generalWaterUpto300', 0)
        elif facility == 'सामान्य पाणीकर ३०१ ते ७०० चौ. फु.':
            return getattr(water_slab_settings, 'generalWater301_700', 0)
        elif facility == 'सामान्य पाणीकर ७०० चौ. फु. वरील':
            return getattr(water_slab_settings, 'generalWaterAbove700', 0)
        return 0
    total_area = round(prop.totalAreaSqFt or 0, 2)
    # Calculate totalHouseTax as the sum of all houseTax in constructions (excluding 'खाली जागा')
    total_house_tax = sum([
        c.houseTax or 0
        for c in prop.constructions
        # if not getattr(c.construction_type, 'name', '').strip().startswith('खाली जागा')
    ])
    if khaliJaga:
        total_house_tax += sum([item.get("houseTax", 0) for item in khaliJaga])
    
    # Calculate total capital value (excluding khali jagas)
    total_capital_value = sum([c.capitalValue or 0 for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")])
    if khaliJaga:
            total_capital_value += sum([item.get("capitalValue", 0) for item in khaliJaga])
    todays_date = date.today().strftime("%d-%m-%Y")
    # Calculate total construction area in foot and meter (excluding khali jagas)
    # Respect property unit: if inputs are in meters, compute meters first; if in feet, compute feet first
    unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
    if unit == 'sqm':
        total_construction_area_meter = round(sum([(c.length or 0) * (c.width or 0) for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")]), 2)
        total_construction_area_foot = round(total_construction_area_meter / 0.092903, 2)
    else:
        total_construction_area_foot = round(sum([(c.length or 0) * (c.width or 0) for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")]), 2)
        total_construction_area_meter = round(total_construction_area_foot * 0.092903, 2)   
    year_from = datetime.now().year
    year_to = year_from + 3
    # Force totals to zero when tax not applicable
    if prop.karLaguNahi:
        total_capital_value = 0
        total_house_tax = 0
    response = {
        "id": str(prop.anuKramank),
        "srNo": prop.anuKramank,
        "propertyNumber": str(prop.malmattaKramank),
        "propertyDescription": property_description,
        "gramPanchayat": gram_panchayat.name if gram_panchayat else None,
        "village": prop.village.name if hasattr(prop, 'village') and prop.village else None,
        "taluka": taluka.name if taluka else None,
        "jilha": district.name if district else None,
        "yearFrom" : str(year_from) + "-" + str(year_from + 1),
        "yearTo": str(year_to) + "-" + str(year_to + 1),
        "todays_date" : todays_date,
        "photoURL": photo_url,
        "bank_qr_code": None,
        "QRcodeURL": None,
        "total_arearinfoot": round(prop.totalAreaSqFt or 0, 2),
        "totalareainmeters": round((prop.totalAreaSqFt or 0) * 0.092903, 2),
        "occupantName": owner.occupantName if owner else None,
        "aadharNumber": owner.aadhaarNumber if owner else None,
        "ownerName": owner.name if owner else None,
        "ownerWifeName":owner.wifeName if owner else None,
        "mobileNumber": owner.mobileNumber if owner else None,
        "roadName": prop.streetName,
        "cityWardGatNumber": prop.citySurveyOrGatNumber,
        "areaEast": prop.eastLength,
        "areaWest": prop.westLength,
        "areaNorth": prop.northLength,
        "areaSouth": prop.southLength,
        "totalArea": round(prop.totalAreaSqFt or 0, 2),
        "boundaryEast": prop.eastBoundary,
        "boundaryWest": prop.westBoundary,
        "boundaryNorth": prop.northBoundary,
        "boundarySouth": prop.southBoundary,
        "removeLightHealthTax": prop.divaArogyaKar,
        "applyCleaningTax": prop.safaiKar,
        "applyToiletTax": prop.shauchalayKar,
        "taxNotApplicable": prop.karLaguNahi,
        "khaliJaga": khaliJaga,
        "constructionType": constructionType,
        "waterFacility1": prop.waterFacility1,
        "waterFacility2": prop.waterFacility2,
        "toilet": str(prop.toilet) if prop.toilet is not None else "",
        "house": prop.roofType,
        "totalCapitalValue": int(total_capital_value if not prop.karLaguNahi else 0),
        "totalHouseTax": int(total_house_tax if not prop.karLaguNahi else 0),
        "totalconstructionareainfoot": total_construction_area_foot,
        "totalconstructionareainmeter": total_construction_area_meter,
        "housingUnit": prop.areaUnit,
        "lightingTax": 0 if prop.karLaguNahi else (get_tax_by_area(total_area, 'light') if not prop.divaArogyaKar else 0),
        "healthTax": 0 if prop.karLaguNahi else (get_tax_by_area(total_area, 'health') if not prop.divaArogyaKar else 0),
        "waterTax": 0,
        "cleaningTax": 0 if prop.karLaguNahi else (get_tax_by_area(total_area, 'cleaning') if prop.safaiKar else 0),
        "toiletTax": 0 if prop.karLaguNahi else (get_tax_by_area(total_area, 'bathroom') if prop.shauchalayKar else 0),
        "sapanikar": 0 if prop.karLaguNahi else get_water_facility_price(prop.waterFacility1),
        "vpanikar": 0 if prop.karLaguNahi else get_water_facility_price(prop.waterFacility2),
        "totaltax": 0,
        "userId": owner_ids,
        "villageId": str(prop.village_id),
        "creationAt": datetime.now(),
        "updationAt": datetime.now(),
        "remarks" : prop.remarks
    }
    # Calculate total tax as sum of houseTax in all constructions (excluding 'खाली जागा') plus lightingTax, healthTax, toiletTax, cleaningTax, sapanikar, and vpanikar
    house_tax_sum = response['totalHouseTax'] if not prop.karLaguNahi else 0
    totaltax = 0 if prop.karLaguNahi else (
        house_tax_sum +
        response.get('lightingTax', 0) +
        response.get('healthTax', 0) +
        response.get('toiletTax', 0) +
        response.get('cleaningTax', 0) +
        response.get('sapanikar', 0) +
        response.get('vpanikar', 0)
    )
    response['totaltax'] = totaltax
    # Fetch Namuna8SettingChecklist row
    checklist = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id).first()
    checklist_fields = {}
    if checklist:
        checklist_dict = checklist.__dict__
        checklist_fields = {k: v for k, v in checklist_dict.items() if k not in ('id', 'createdAt', 'updatedAt', 'roundupArea', '_sa_instance_state')}
    # Add checklist fields at the end
    response.update(checklist_fields)
    # Set QRcodeURL if QR code exists (single property)
    # Use location-based QR path
    qr_path = os.path.join("uploaded_images", "qrcode", str(prop.district_id), str(prop.taluka_id), str(prop.gram_panchayat_id), str(prop.village_id),str(prop.anuKramank), "qrcode.png")
    if os.path.exists(qr_path):
        response["QRcodeURL"] = f"{backend_url}/namuna8/property_qrcode/{prop.anuKramank}?district_id={prop.district_id}&taluka_id={prop.taluka_id}&gram_panchayat_id={prop.gram_panchayat_id}&village_id={prop.village_id}"
    else:
        response["QRcodeURL"] = None
    
    # Set bank_qr_code only if gram panchayat image exists
    from location_management import helpers
    image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
    if image_path and os.path.exists(image_path):
        response["bank_qr_code"] = f"{backend_url}/location/districts/{district_id}/talukas/{taluka_id}/gram-panchayats/{gram_panchayat_id}/image"
    
    # Coerce all numeric fields to integers except 'length' and 'width'
    _deep_round_numbers(response)
    return response 

@router.get("/property_records_by_village/{village_id}")
def get_property_records_by_village(
    village_id: int, 
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    
    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail=f"Taluka {taluka_id} does not belong to district {district_id}")
    
    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail=f"Gram Panchayat {gram_panchayat_id} does not belong to taluka {taluka_id}")
    
    # Validate that the village belongs to the specified gram panchayat
    village = db.query(models.Village).filter(models.Village.id == village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail=f"Village {village_id} not found")
    
    if village.gram_panchayat_id != gram_panchayat_id:
        raise HTTPException(status_code=400, detail=f"Village {village_id} does not belong to gram panchayat {gram_panchayat_id}")
    
    properties = db.query(models.Property).filter(models.Property.village_id == village_id).all()
    results = []
    # Fetch Namuna8SettingChecklist row only once
    checklist = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id).first()
    checklist_fields = {}
    if checklist:
        checklist_dict = checklist.__dict__
        checklist_fields = {k: v for k, v in checklist_dict.items() if k not in ('id', 'createdAt', 'updatedAt', 'roundupArea', '_sa_instance_state')}
    for prop in properties:
        owner_ids = [o.id for o in prop.owners]
        property_types = [c.construction_type.name for c in prop.constructions]
        property_description = ", ".join(property_types)
        khali_jaga_types = [c for c in prop.constructions if c.construction_type.name.strip() == "खाली जागा"]
        khaliJaga = []
        if getattr(prop, 'vacantLandType', None) not in [None, '', 'null']:
            # Compute khali area in both sqm and sqft based on stored unit
            unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
            if unit == 'sqm':
                total_area_m = round(prop.totalArea or 0, 2)
                used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in prop.constructions), 2)
            else:
                total_area_m = round((prop.totalAreaSqFt or 0) * 0.092903, 2)
                used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in prop.constructions) * 0.092903, 2)
            khali_area_m = round(max(total_area_m - used_area_m, 0), 2)
            khali_area = round(khali_area_m / 0.092903, 2)
            # Find the bandhmastache_dar for vacantLandType construction type
            khali_jaga_rate = 0
            vacant_construction_type = None
            if prop.vacantLandType:
                # Query database directly for the construction type, regardless of property constructions
                vacant_construction_type = db.query(models.ConstructionType).filter(models.ConstructionType.name == prop.vacantLandType).first()
                if vacant_construction_type:
                    khali_jaga_rate = getattr(vacant_construction_type, 'bandhmastache_dar', 0)
                else:
                    # Fallback: try to find any construction type with similar name
                    similar_construction = db.query(models.ConstructionType).filter(models.ConstructionType.name.like(f"%{prop.vacantLandType}%")).first()
                    if similar_construction:
                        khali_jaga_rate = getattr(similar_construction, 'bandhmastache_dar', 0)
            # Calculate capital value and house tax for khali jaga using same logic as Namuna8
            if khali_area > 0:
                # Ensure khali_area_m is defined in this scope
                unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
                khali_area_m = round(khali_area, 2) if unit == 'sqm' else round(khali_area * 0.092903, 2)
                # Get construction type for khali jaga
                khali_construction_type = db.query(models.ConstructionType).filter(models.ConstructionType.name == "खाली जागा").first()
                
                if khali_construction_type:
                    # Get user formula preference - same as Namuna8
                    userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
                    
                    if userFormulaPreference:
                        formula1 = userFormulaPreference.capitalFormula1
                        formula2 = userFormulaPreference.capitalFormula2
                    else:
                        formula1 = None
                        formula2 = None
                    
                    # Calculate area in meters - same as Namuna8
                    AreaInMeter = khali_area_m
                    AnnualLandValueRate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                    ConstructionRateAsPerConstruction = khali_construction_type.bandhmastache_dar
                    depreciationRate = calculate_depreciation_rate(datetime.now().year, khali_construction_type.name)
                    
                    # Get usage weightage factor - same as Namuna8
                    weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
                    usageBasedBuildingWeightageFactor = weightage_map.get(prop.vacantLandType, 1)
                    
                    # Calculate capital value - exact same logic as Namuna8
                    if formula1:
                        capital_value = ((AreaInMeter * AnnualLandValueRate) + (AreaInMeter * ConstructionRateAsPerConstruction * depreciationRate)) * usageBasedBuildingWeightageFactor
                    else:
                        capital_value = AreaInMeter * AnnualLandValueRate * depreciationRate * usageBasedBuildingWeightageFactor
                    capital_value = round(capital_value, 2)
                    
                    # Calculate house tax - exact same logic as Namuna8
                    house_tax = round((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value)
                else:
                    capital_value = 0
                    house_tax = 0
                
                khaliJaga = [{
                    "constructiontype": "खाली जागा",
                    "length": round(khali_area, 2),
                    "width": 1,
                    "year": datetime.now().year,
                    "rate": khali_jaga_rate,
                    "floor": "तळमजला",
                    "usage": prop.vacantLandType,
                    "capitalValue": 0 if prop.karLaguNahi else round(capital_value, 2),
                    "houseTax": 0 if prop.karLaguNahi else house_tax,
                    "usageBasedBuildingWeightageFactor": weightage_map.get(getattr(khali_construction_type, 'bharank', None), 1),
                    "taxRates": getattr(khali_construction_type, 'rate', 0) if khali_area > 0 else 0,
                    "totalkhalijagaareainfoot": round(khali_area, 2),
                    "totalkhalijagaareainmeters": round(khali_area_m, 2)
                }]
        # else: khaliJaga remains []
        # Fetch weightage mapping for usage
        weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
        constructionType = [
            {
                "type": c.construction_type.name,
                "length": c.length,
                "width": c.width,
                "year": c.constructionYear,
                "rate": getattr(c.construction_type, 'bandhmastache_dar', 0),
                "floor": c.floor,
                "usage": getattr(c, 'bharank', None),
                "capitalValue": c.capitalValue,
                "houseTax": c.houseTax,
                "depreciation_rate": calculate_depreciation_rate(c.constructionYear, c.construction_type.name),
                "usageBasedBuildingWeightageFactor": weightage_map.get(getattr(c, 'bharank', None), 1),
                "taxRates": getattr(c.construction_type, 'rate', 0),
            }
            for c in prop.constructions
        ]
        owner = prop.owners[0] if prop.owners else None
        settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
        water_settings = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
        water_slab_settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
        def get_tax_by_area(area, field):
            if not settings:
                return 0
            if area is None:
                area = 0
            if area <= 300:
                return getattr(settings, field + 'Upto300', 0) or 0
            elif 301 <= area <= 700:
                return getattr(settings, field + '301_700', 0) or 0
            else:
                return getattr(settings, field + 'Above700', 0) or 0
        def get_water_facility_price(facility):
            if not facility:
                return 0
            if not water_settings or not water_slab_settings:
                return 0
            # Accept both spellings for 'सामान्य पाणीकर' and 'सामान्य पाणीकर'
            if facility in ['सामान्य पाणीकर', 'सामान्य पाणीकर']:
                return getattr(water_settings, 'generalWater', 0)
            elif facility == 'घरगुती नळ':
                return getattr(water_settings, 'houseTax', 0)
            elif facility == 'व्यावसायिक नळ':
                return getattr(water_settings, 'commercialTax', 0)
            elif facility == 'करास पात्र नसलेली इमारत':
                return getattr(water_settings, 'exemptRate', 0)
            elif facility == 'सामान्य पाणीकर १ ते ३०० चौ. फु.':
                return getattr(water_slab_settings, 'generalWaterUpto300', 0)
            elif facility == 'सामान्य पाणीकर ३०१ ते ७०० चौ. फु.':
                return getattr(water_slab_settings, 'generalWater301_700', 0)
            elif facility == 'सामान्य पाणीकर ७०० चौ. फु. वरील':
                return getattr(water_slab_settings, 'generalWaterAbove700', 0)
            return 0
        # Normalize total area based on property unit
        unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
        if unit == 'sqm':
            total_area_m = round(prop.totalArea or 0, 2)
            total_area_sqft = round((prop.totalArea or 0) / 0.092903, 2)
        else:
            total_area_sqft = round(prop.totalAreaSqFt or 0, 2)
            total_area_m = round((prop.totalAreaSqFt or 0) * 0.092903, 2)
        # Use sqft for slabbed area taxes (301-700 etc. are in sqft)
        total_area = total_area_sqft
        # Calculate totalHouseTax as the sum of all houseTax in constructions (excluding 'खाली जागा')
        total_house_tax = sum([
            c.houseTax or 0
            for c in prop.constructions
            # if not getattr(c.construction_type, 'name', '').strip().startswith('खाली जागा')
        ])
        if khaliJaga:
            total_house_tax += sum([item.get("houseTax", 0) for item in khaliJaga])
        total_capital_value = sum([c.capitalValue or 0 for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")])
        if khaliJaga:
                 total_capital_value += sum([item.get("capitalValue", 0) for item in khaliJaga])
        # Construction area totals aligned with unit handling
        if unit == 'sqm':
            total_construction_area_meter = round(sum([(c.length or 0) * (c.width or 0) for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")]), 2)
            total_construction_area_foot = round(total_construction_area_meter / 0.092903, 2)
        else:
            total_construction_area_foot = round(sum([(c.length or 0) * (c.width or 0) for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")]), 2)
            total_construction_area_meter = round(total_construction_area_foot * 0.092903, 2)
        year_from = datetime.now().year
        year_to = year_from + 3
        response = {
            "id": str(prop.anuKramank),
            "anuKramank": prop.anuKramank,
            "srNo": prop.anuKramank,
            "propertyNumber": str(prop.malmattaKramank),
            "propertyDescription": property_description,
            "gramPanchayat": gram_panchayat.name if gram_panchayat else None,
            "village": prop.village.name if hasattr(prop, 'village') and prop.village else None,
            "taluka": taluka.name if taluka else None,
            "jilha": district.name if district else None,
            "yearFrom" : str(year_from) + "-" + str(year_from + 1),
            "yearTo": str(year_to) + "-" + str(year_to + 1),
            "photoURL": None,
            "QRcodeURL": None,
            "total_arearinfoot": total_area_sqft,
            "totalareainmeters": total_area_m,
            "occupantName": owner.occupantName if owner else None,
            "aadharNumber": owner.aadhaarNumber if owner else None,
            "ownerName": owner.name if owner else None,
            "mobileNumber": owner.mobileNumber if owner else None,
            "roadName": prop.streetName,
            "cityWardGatNumber": prop.citySurveyOrGatNumber,
            "areaEast": prop.eastLength,
            "areaWest": prop.westLength,
            "areaNorth": prop.northLength,
            "areaSouth": prop.southLength,
            "totalArea": total_area_sqft,
            "boundaryEast": prop.eastBoundary,
            "boundaryWest": prop.westBoundary,
            "boundaryNorth": prop.northBoundary,
            "boundarySouth": prop.southBoundary,
            "removeLightHealthTax": prop.divaArogyaKar,
            "applyCleaningTax": prop.safaiKar,
            "applyToiletTax": prop.shauchalayKar,
            "taxNotApplicable": prop.karLaguNahi,
            "khaliJaga": khaliJaga,
            "constructionType": constructionType,
            "waterFacility1": prop.waterFacility1,
            "waterFacility2": prop.waterFacility2,
            "toilet": str(prop.toilet) if prop.toilet is not None else "",
            "house": prop.roofType,
            "totalCapitalValue": int(total_capital_value),
            "totalHouseTax": int(total_house_tax),
            "totalconstructionareainfoot": total_construction_area_foot,
            "totalconstructionareainmeter": total_construction_area_meter,
            "housingUnit": prop.areaUnit,
            "lightingTax": get_tax_by_area(total_area, 'light') if not prop.divaArogyaKar else 0,
            "healthTax": get_tax_by_area(total_area, 'health') if not prop.divaArogyaKar else 0,
            "waterTax": 0,
            "cleaningTax": get_tax_by_area(total_area, 'cleaning') if prop.safaiKar else 0,
            "toiletTax": get_tax_by_area(total_area, 'bathroom') if prop.shauchalayKar else 0,
            "sapanikar": get_water_facility_price(prop.waterFacility1),
            "vpanikar": get_water_facility_price(prop.waterFacility2),
            "totaltax": 0,
            "remarks" : prop.remarks
        }
        # Calculate total tax as sum of houseTax in all constructions (excluding 'खाली जागा') plus lightingTax, healthTax, toiletTax, cleaningTax, sapanikar, and vpanikar
        # house_tax_sum = sum([
        #     c.houseTax or 0
        #     for c in prop.constructions
        #     # if not getattr(c.construction_type, 'name', '').strip().startswith('खाली जागा')
        # ])
        house_tax_sum = 0 if prop.karLaguNahi else response['totalHouseTax']
        totaltax = 0 if prop.karLaguNahi else (
            house_tax_sum +
            response.get('lightingTax', 0) +
            response.get('healthTax', 0) +
            response.get('toiletTax', 0) +
            response.get('cleaningTax', 0) +
            response.get('sapanikar', 0) +
            response.get('vpanikar', 0)
        )
        response['totaltax'] = totaltax
        # Find the first owner with a non-null ownerPhoto
        photo_url = None
        for o in prop.owners:
            if getattr(o, 'ownerPhoto', None):
                photo_url = f"{backend_url}/{o.ownerPhoto.replace(os.sep, '/')}"
                break
        response["photoURL"] = photo_url
        response["bank_qr_code"] = None
        # Set QRcodeURL if QR code exists (bulk)
        # Use location-based QR path
        qr_path = os.path.join("uploaded_images", "qrcode", str(prop.district_id), str(prop.taluka_id), str(prop.gram_panchayat_id),str(prop.village_id), str(prop.anuKramank), "qrcode.png")
        if os.path.exists(qr_path):
            response["QRcodeURL"] = f"{backend_url}/namuna8/property_qrcode/{prop.anuKramank}?district_id={prop.district_id}&taluka_id={prop.taluka_id}&gram_panchayat_id={prop.gram_panchayat_id}&village_id={prop.village_id}"
        else:
            response["QRcodeURL"] = None
        
        # Set bank_qr_code only if gram panchayat image exists (bulk)
        from location_management import helpers
        image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
        if image_path and os.path.exists(image_path):
            response["bank_qr_code"] = f"{backend_url}/location/districts/{district_id}/talukas/{taluka_id}/gram-panchayats/{gram_panchayat_id}/image"
        
        # Add checklist fields to the response
        response.update(checklist_fields)
        # Coerce all numeric fields to integers except 'length' and 'width'
        _deep_round_numbers(response)
        results.append(response)
    return results 

@router.get("/property_records_by_gram_panchayat/{gram_panchayat_id}")
def get_property_records_by_gram_panchayat(
    gram_panchayat_id: int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")

    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail=f"Taluka {taluka_id} does not belong to district {district_id}")

    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail=f"Gram Panchayat {gram_panchayat_id} does not belong to taluka {taluka_id}")

    # Get all villages for the given gram panchayat
    villages = db.query(models.Village).filter(models.Village.gram_panchayat_id == gram_panchayat_id).all()

    # Fetch Namuna8SettingChecklist row only once
    checklist = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id).first()
    checklist_fields = {}
    if checklist:
        checklist_dict = checklist.__dict__
        checklist_fields = {k: v for k, v in checklist_dict.items() if k not in ('id', 'createdAt', 'updatedAt', 'roundupArea', '_sa_instance_state')}

    # Structure response by villages
    response_data = {}
    
    for village in villages:
        village_properties = []
        properties = db.query(models.Property).filter(models.Property.village_id == village.id).all()
        
        for prop in properties:
            owner_ids = [o.id for o in prop.owners]
            property_types = [c.construction_type.name for c in prop.constructions]
            property_description = ", ".join(property_types)

            khaliJaga = []
            if getattr(prop, 'vacantLandType', None) not in [None, '', 'null']:
                unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
                if unit == 'sqm':
                    total_area_m = round(prop.totalArea or 0, 2)
                    used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in prop.constructions), 2)
                else:
                    total_area_m = round((prop.totalAreaSqFt or 0) * 0.092903, 2)
                    used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in prop.constructions) * 0.092903, 2)
                khali_area_m = round(max(total_area_m - used_area_m, 0), 2)
                khali_area = round(khali_area_m / 0.092903, 2)
                khali_jaga_rate = 0
                vacant_construction_type = None

                if prop.vacantLandType:
                    vacant_construction_type = db.query(models.ConstructionType).filter(models.ConstructionType.name == prop.vacantLandType).first()
                    if vacant_construction_type:
                        khali_jaga_rate = getattr(vacant_construction_type, 'bandhmastache_dar', 0)
                    else:
                        similar_construction = db.query(models.ConstructionType).filter(models.ConstructionType.name.like(f"%{prop.vacantLandType}%")).first()
                        if similar_construction:
                            khali_jaga_rate = getattr(similar_construction, 'bandhmastache_dar', 0)

                if khali_area > 0:
                    khali_construction_type = db.query(models.ConstructionType).filter(models.ConstructionType.name == "खाली जागा").first()

                    if khali_construction_type:
                        userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()

                        if userFormulaPreference:
                            formula1 = userFormulaPreference.capitalFormula1
                            formula2 = userFormulaPreference.capitalFormula2
                        else:
                            formula1 = None
                            formula2 = None

                        AreaInMeter = khali_area_m
                        AnnualLandValueRate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                        ConstructionRateAsPerConstruction = khali_construction_type.bandhmastache_dar
                        depreciationRate = calculate_depreciation_rate(datetime.now().year, khali_construction_type.name)

                        weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
                        usageBasedBuildingWeightageFactor = weightage_map.get(prop.vacantLandType, 1)

                        if formula1:
                            capital_value = ((AreaInMeter * AnnualLandValueRate) + (AreaInMeter * ConstructionRateAsPerConstruction * depreciationRate)) * usageBasedBuildingWeightageFactor
                        else:
                            capital_value = AreaInMeter * AnnualLandValueRate * depreciationRate * usageBasedBuildingWeightageFactor

                        house_tax = round((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value)
                    else:
                        capital_value = 0
                        house_tax = 0

                    khaliJaga = [{
                        "constructiontype": "खाली जागा",
                        "length": round(khali_area, 2),
                        "width": 1,
                        "year": datetime.now().year,
                        "rate": khali_jaga_rate,
                        "floor": "तळमजला",
                        "usage": prop.vacantLandType,
                        "capitalValue": 0 if prop.karLaguNahi else capital_value,
                        "houseTax": 0 if prop.karLaguNahi else house_tax,
                        "usageBasedBuildingWeightageFactor":  weightage_map.get(getattr(khali_construction_type, 'bharank', None), 1),
                        "taxRates": 0 if prop.karLaguNahi else getattr(khali_construction_type, 'rate', 0) if khali_area > 0 else 0,
                        "totalkhalijagaareainfoot": round(khali_area, 2),
                        "totalkhalijagaareainmeters": round(khali_area_m, 2)
                    }]

            weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
            constructionType = [
                {
                    "type": c.construction_type.name,
                    "length": c.length,
                    "width": c.width,
                    "year": c.constructionYear,
                    "rate": getattr(c.construction_type, 'bandhmastache_dar', 0),
                    "floor": c.floor,
                    "usage": getattr(c, 'bharank', None),
                    "capitalValue": c.capitalValue,
                    "houseTax": c.houseTax,
                    "depreciation_rate": calculate_depreciation_rate(c.constructionYear, c.construction_type.name),
                    "usageBasedBuildingWeightageFactor": weightage_map.get(getattr(c, 'bharank', None), 1),
                    "taxRates": getattr(c.construction_type, 'rate', 0),
                }
                for c in prop.constructions
            ]
            owner = prop.owners[0] if prop.owners else None

            settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
            water_settings = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
            water_slab_settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()

            def get_tax_by_area(area, field):
                if not settings:
                    return 0
                if area is None:
                    area = 0
                if area <= 300:
                    return getattr(settings, field + 'Upto300', 0) or 0
                elif 301 <= area <= 700:
                    return getattr(settings, field + '301_700', 0) or 0
                else:
                    return getattr(settings, field + 'Above700', 0) or 0

            def get_water_facility_price(facility):
                if not facility:
                    return 0
                if not water_settings or not water_slab_settings:
                    return 0
                if facility in ['सामान्य पाणीकर', 'सामान्य पाणीकर']:
                    return getattr(water_settings, 'generalWater', 0)
                elif facility == 'घरगुती नळ':
                    return getattr(water_settings, 'houseTax', 0)
                elif facility == 'व्यावसायिक नळ':
                    return getattr(water_settings, 'commercialTax', 0)
                elif facility == 'करास पात्र नसलेली इमारत':
                    return getattr(water_settings, 'exemptRate', 0)
                elif facility == 'सामान्य पाणीकर १ ते ३०० चौ. फु.':
                    return getattr(water_slab_settings, 'generalWaterUpto300', 0)
                elif facility == 'सामान्य पाणीकर ३०१ ते ७०० चौ. फु.':
                    return getattr(water_slab_settings, 'generalWater301_700', 0)
                elif facility == 'सामान्य पाणीकर ७०० चौ. फु. वरील':
                    return getattr(water_slab_settings, 'generalWaterAbove700', 0)
                return 0

            # Normalize total area based on property unit (align with village endpoint)
            unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
            if unit == 'sqm':
                total_area_m = round(prop.totalArea or 0, 2)
                total_area_sqft = round((prop.totalArea or 0) / 0.092903, 2)
            else:
                total_area_sqft = round(prop.totalAreaSqFt or 0, 2)
                total_area_m = round((prop.totalAreaSqFt or 0) * 0.092903, 2)
            # Use sqft for slabbed area taxes (301-700 etc. are in sqft)
            total_area = total_area_sqft
            total_house_tax = sum([
                c.houseTax or 0
                for c in prop.constructions
            ])
            if khaliJaga:
                 total_house_tax += sum([item.get("houseTax", 0) for item in khaliJaga])
            total_capital_value = sum([c.capitalValue or 0 for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")])
            if khaliJaga:
                 total_capital_value += sum([item.get("capitalValue", 0) for item in khaliJaga])
            # Construction area totals aligned with unit handling
            if unit == 'sqm':
                total_construction_area_meter = round(sum([(c.length or 0) * (c.width or 0) for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")]), 2)
                total_construction_area_foot = round(total_construction_area_meter / 0.092903, 2)
            else:
                total_construction_area_foot = round(sum([(c.length or 0) * (c.width or 0) for c in prop.constructions if not c.construction_type.name.strip().startswith("खाली जागा")]), 2)
                total_construction_area_meter = round(total_construction_area_foot * 0.092903, 2)
            year_from = datetime.now().year
            year_to = year_from + 3
            todays_date = date.today().strftime("%d-%m-%Y")

            response = {
                "id": str(prop.anuKramank),
                "srNo": prop.anuKramank,
                "propertyNumber": str(prop.malmattaKramank),
                "propertyDescription": property_description,
                "gramPanchayat": gram_panchayat.name if gram_panchayat else None,
                "village": village.name if village else None,
                "taluka": taluka.name if taluka else None,
                "jilha": district.name if district else None,
                "yearFrom": year_from,
                "yearFrom" : str(year_from) + "-" + str(year_from + 1),
                "yearTo": str(year_to) + "-" + str(year_to + 1),
                "photoURL": None,
                "bank_qr_code": None,
                "QRcodeURL": None,
                "total_arearinfoot": total_area_sqft,
                "totalareainmeters": total_area_m,
                "occupantName": owner.occupantName if owner else None,
                "aadharNumber": owner.aadhaarNumber if owner else None,
                "ownerName": owner.name if owner else None,
                "ownerWifeName":owner.wifeName if owner else None,
                "mobileNumber": owner.mobileNumber if owner else None,
                "roadName": prop.streetName,
                "cityWardGatNumber": prop.citySurveyOrGatNumber,
                "areaEast": prop.eastLength,
                "areaWest": prop.westLength,
                "areaNorth": prop.northLength,
                "areaSouth": prop.southLength,
                "totalArea": total_area_sqft,
                "boundaryEast": prop.eastBoundary,
                "boundaryWest": prop.westBoundary,
                "boundaryNorth": prop.northBoundary,
                "boundarySouth": prop.southBoundary,
                "removeLightHealthTax": prop.divaArogyaKar,
                "applyCleaningTax": prop.safaiKar,
                "applyToiletTax": prop.shauchalayKar,
                "taxNotApplicable": prop.karLaguNahi,
                "khaliJaga": khaliJaga,
                "constructionType": constructionType,
                "waterFacility1": prop.waterFacility1,
                "waterFacility2": prop.waterFacility2,
                "toilet": str(prop.toilet) if prop.toilet is not None else "",
                "house": prop.roofType,
                "totalCapitalValue": int(total_capital_value),
                "totalHouseTax": int(total_house_tax),
                "totalconstructionareainfoot": total_construction_area_foot,
                "totalconstructionareainmeter": total_construction_area_meter,
                "housingUnit": prop.areaUnit,
                "lightingTax": get_tax_by_area(total_area, 'light') if not prop.divaArogyaKar else 0,
                "healthTax": get_tax_by_area(total_area, 'health') if not prop.divaArogyaKar else 0,
                "waterTax": 0,
                "cleaningTax": get_tax_by_area(total_area, 'cleaning') if prop.safaiKar else 0,
                "toiletTax": get_tax_by_area(total_area, 'bathroom') if prop.shauchalayKar else 0,
                "sapanikar": get_water_facility_price(prop.waterFacility1),
                "vpanikar": get_water_facility_price(prop.waterFacility2),
                "totaltax": 0,
                "userId": owner_ids,
                "villageId": str(village.id),
                "creationAt": datetime.now(),
                "updationAt": datetime.now(),
                "remarks" : prop.remarks
            }

            house_tax_sum = response['totalHouseTax']
            totaltax = (
                house_tax_sum +
                response.get('lightingTax', 0) +
                response.get('healthTax', 0) +
                response.get('toiletTax', 0) +
                response.get('cleaningTax', 0) +
                response.get('sapanikar', 0) +
                response.get('vpanikar', 0)
            )
            response['totaltax'] = totaltax

            photo_url = None
            for o in prop.owners:
                if getattr(o, 'ownerPhoto', None):
                    photo_url = f"{backend_url}/{o.ownerPhoto.replace(os.sep, '/')}"
                    break
            response["photoURL"] = photo_url

            qr_path = os.path.join("uploaded_images", "qrcode", str(prop.district_id), str(prop.taluka_id), str(prop.gram_panchayat_id),str(prop.village_id), str(prop.anuKramank), "qrcode.png")
            if os.path.exists(qr_path):
                response["QRcodeURL"] = f"{backend_url}/namuna8/property_qrcode/{prop.anuKramank}?district_id={prop.district_id}&taluka_id={prop.taluka_id}&gram_panchayat_id={prop.gram_panchayat_id}&village_id={prop.village_id}"
            else:
                response["QRcodeURL"] = None

            from location_management import helpers
            image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
            if image_path and os.path.exists(image_path):
                response["bank_qr_code"] = f"{backend_url}/location/districts/{district_id}/talukas/{taluka_id}/gram-panchayats/{gram_panchayat_id}/image"

            # Coerce all numeric fields to integers except 'length' and 'width'
            _deep_round_numbers(response)
            response.update(checklist_fields)
            village_properties.append(response)
        
        # Add village properties to response data with village name as key
        if village_properties:  # Only add villages that have properties
            response_data[f"{village.name}"] = village_properties

    return response_data 